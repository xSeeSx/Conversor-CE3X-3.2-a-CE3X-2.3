#define UNICODE
#define _UNICODE
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <commdlg.h>
#include <commctrl.h>
#include <shellapi.h>
#include <stdio.h>
#include <wchar.h>
#include <string.h>

#define PATHCAP 32768
#define COMMANDCAP 65536
#define RESPONSECAP 131072
#define IDC_SOURCE 101
#define IDC_BROWSE 102
#define IDC_CONVERT 103
#define IDC_OPEN 104
#define IDC_DIAGNOSTIC 105
#define IDC_ATTACHMENT 106
#define IDC_NOTES 107
#define IDC_HELP 108
#define IDC_DETAILS 109
#define IDC_REPORT 110
#define IDC_TITLE 111
#define IDC_VERSION 112
#define IDC_INPUT_LABEL 113
#define IDC_OUTPUT_LABEL 114
#define IDC_OUTPUT_NAME 115
#define IDC_OUTPUT_HELP 116
#define IDC_NOTICE 117
#define IDC_NOTES_LABEL 118
#define IDC_ATTACHMENT_LABEL 119
#define IDC_RETENTION 120
#define UI_BACKGROUND RGB(245, 246, 249)
#define UI_HEADER RGB(234, 237, 247)
#define UI_BORDER RGB(204, 210, 223)
#define UI_TEXT RGB(32, 38, 50)
#define UI_ACCENT RGB(58, 69, 154)

static HWND window, sourceEdit, convertButton, diagnosticButton, openButton, notesEdit, reportEdit, attachmentLabel;
static HFONT font, titleFont, strongFont, smallFont;
static HBRUSH backgroundBrush, panelBrush, headerBrush;
static HWND detailControls[6];
static int detailCount, detailsVisible, statusVisible, uiDpi = 96;
static void layoutWindow(void);
static WCHAR baseDir[PATHCAP], lastOutput[PATHCAP], attachedPath[PATHCAP], lastReport[PATHCAP + 8192];
static HANDLE engineInput, engineOutput;
static PROCESS_INFORMATION engine;
static int busy, hasAttempt, operation, selfTestPassed;
static char response[RESPONSECAP];
static DWORD responseSize;

static int exists(const WCHAR *path) {
    DWORD attributes = GetFileAttributesW(path);
    return attributes != INVALID_FILE_ATTRIBUTES && !(attributes & FILE_ATTRIBUTE_DIRECTORY);
}
static void report(const WCHAR *text) {
    wcsncpy(lastReport, text, PATHCAP + 8191); lastReport[PATHCAP + 8191] = 0;
    if (reportEdit) {
        SetWindowTextW(reportEdit, lastReport);
        if (!statusVisible && text[0]) { statusVisible = 1; ShowWindow(reportEdit, SW_SHOW); layoutWindow(); }
    }
}
static void setBusy(int value) {
    busy = value;
    if (!window) return;
    EnableWindow(sourceEdit, !value);
    EnableWindow(GetDlgItem(window, IDC_BROWSE), !value);
    EnableWindow(convertButton, !value);
    EnableWindow(diagnosticButton, !value && hasAttempt);
    EnableWindow(GetDlgItem(window, IDC_ATTACHMENT), !value && hasAttempt);
    EnableWindow(openButton, !value && lastOutput[0]);
}
static void outputName(const WCHAR *source, WCHAR *output) {
    wcsncpy(output, source, PATHCAP - 1); output[PATHCAP - 1] = 0;
    WCHAR *slash = wcsrchr(output, L'\\'), *forward = wcsrchr(output, L'/'), *dot = wcsrchr(output, L'.');
    if (forward && (!slash || forward > slash)) slash = forward;
    if (dot && (!slash || dot > slash)) *dot = 0;
    if (wcslen(output) + 13 < PATHCAP) wcscat(output, L"_CE3X2.3.cex");
    else output[0] = 0;
}
// CreateProcessW arguments are quoted directly; no command shell is involved.
static int addArg(WCHAR *command, size_t capacity, const WCHAR *value) {
    size_t length = wcslen(command);
    if (length + 4 >= capacity) return 0;
    command[length++] = L' '; command[length++] = L'"';
    while (*value) {
        size_t slashes = 0;
        while (*value == L'\\') { slashes++; value++; }
        size_t count = (*value == L'"' || !*value) ? 2 * slashes : slashes;
        if (*value == L'"') count++;
        if (length + count + 3 >= capacity) return 0;
        while (count--) command[length++] = L'\\';
        if (!*value) break;
        command[length++] = *value++;
    }
    command[length++] = L'"'; command[length] = 0; return 1;
}
static void closeEngine(void) {
    if (engineInput) { CloseHandle(engineInput); engineInput = NULL; }
    if (engineOutput) { CloseHandle(engineOutput); engineOutput = NULL; }
    if (engine.hProcess) {
        WaitForSingleObject(engine.hProcess, 1000);
        CloseHandle(engine.hProcess); CloseHandle(engine.hThread);
        ZeroMemory(&engine, sizeof(engine));
    }
}
static int startEngine(void) {
    DWORD code;
    if (engine.hProcess && GetExitCodeProcess(engine.hProcess, &code) && code == STILL_ACTIVE) return 1;
    closeEngine(); hasAttempt = 0;
    WCHAR python[PATHCAP], script[PATHCAP], command[32768] = L"";
    swprintf(python, PATHCAP, L"%ls\\runtime\\python.exe", baseDir);
    swprintf(script, PATHCAP, L"%ls\\app\\converter.py", baseDir);
    if (!exists(python) || !exists(script)) {
        report(L"Falta el motor. Extrae todo el ZIP y conserva las carpetas app y runtime junto al ejecutable."); return 0;
    }
    const WCHAR *arguments[] = {python, L"-I", L"-X", L"utf8", L"-B", L"-u", script, L"serve"};
    for (int i = 0; i < 8; i++) if (!addArg(command, 32768, arguments[i])) return 0;
    SECURITY_ATTRIBUTES security = {sizeof(security), NULL, TRUE};
    HANDLE childInput = NULL, childOutput = NULL;
    if (!CreatePipe(&engineOutput, &childOutput, &security, 0) ||
        !CreatePipe(&childInput, &engineInput, &security, 0)) goto fail;
    if (!SetHandleInformation(engineOutput, HANDLE_FLAG_INHERIT, 0) ||
        !SetHandleInformation(engineInput, HANDLE_FLAG_INHERIT, 0)) goto fail;
    STARTUPINFOW startup = {0}; startup.cb = sizeof(startup);
    startup.dwFlags = STARTF_USESTDHANDLES | STARTF_USESHOWWINDOW;
    startup.wShowWindow = SW_HIDE;
    startup.hStdInput = childInput; startup.hStdOutput = childOutput; startup.hStdError = childOutput;
    if (!CreateProcessW(python, command + 1, NULL, NULL, TRUE, CREATE_NO_WINDOW, NULL, baseDir, &startup, &engine)) goto fail;
    CloseHandle(childInput); CloseHandle(childOutput); responseSize = 0; return 1;
fail:
    if (childInput) CloseHandle(childInput);
    if (childOutput) CloseHandle(childOutput);
    closeEngine(); report(L"No se pudo iniciar Python. Comprueba que has extraido todo el ZIP."); return 0;
}
// Serialize paths and notes as JSON strings, including quotes and line breaks.
static int appendJson(WCHAR *target, const WCHAR *text) {
    size_t size = wcslen(target);
    if (size + 2 >= COMMANDCAP) return 0;
    target[size++] = L'"';
    for (; *text; text++) {
        if (size + 256 >= COMMANDCAP) return 0;
        if (*text == L'"' || *text == L'\\') { target[size++] = L'\\'; target[size++] = *text; }
        else if (*text < 32) {
            swprintf(target + size, COMMANDCAP - size, L"\\u%04x", (unsigned int)*text); size += 6;
        } else target[size++] = *text;
    }
    target[size++] = L'"'; target[size] = 0; return 1;
}
static int request(const WCHAR *json, int kind) {
    if (!startEngine()) return 0;
    int length = WideCharToMultiByte(CP_UTF8, WC_ERR_INVALID_CHARS, json, -1, NULL, 0, NULL, NULL);
    if (length <= 0) { report(L"Hay caracteres no validos en las rutas o las notas."); return 0; }
    char *bytes = HeapAlloc(GetProcessHeap(), 0, length + 1);
    if (!bytes) return 0;
    WideCharToMultiByte(CP_UTF8, WC_ERR_INVALID_CHARS, json, -1, bytes, length, NULL, NULL);
    bytes[length - 1] = '\n';
    DWORD sent = 0;
    BOOL ok = WriteFile(engineInput, bytes, length, &sent, NULL);
    HeapFree(GetProcessHeap(), 0, bytes);
    if (!ok || sent != (DWORD)length) { closeEngine(); report(L"No se pudo comunicar con el motor."); return 0; }
    responseSize = 0; operation = kind; setBusy(1);
    if (kind == 1) report(L"Convirtiendo y comprobando el archivo...");
    else if (kind == 2) report(L"Guardando el diagnostico solicitado...");
    if (window) SetTimer(window, 1, 100, NULL);
    return 1;
}
static int decisionResult, decisionPreviewSaved, decisionSmokeChoice;
static const WCHAR *decisionPreviewPath;
static int savePreview(HWND target, const WCHAR *path);
static LRESULT CALLBACK DecisionProc(HWND hwnd, UINT msg, WPARAM wp, LPARAM lp) {
    if (msg == WM_COMMAND && (LOWORD(wp) == 501 || LOWORD(wp) == 502 || LOWORD(wp) == IDCANCEL)) {
        decisionResult = LOWORD(wp); DestroyWindow(hwnd); return 0;
    }
    if (msg == WM_CLOSE) { decisionResult = IDCANCEL; DestroyWindow(hwnd); return 0; }
    return DefWindowProcW(hwnd, msg, wp, lp);
}
static int conversionDecision(const WCHAR *message, int canAdapt, int experimental) {
    WNDCLASSW wc = {0}; wc.lpfnWndProc = DecisionProc; wc.hInstance = GetModuleHandleW(NULL);
    wc.lpszClassName = L"CE3XConversionDecision"; wc.hCursor = LoadCursor(NULL, IDC_ARROW);
    wc.hbrBackground = (HBRUSH)(COLOR_WINDOW + 1); RegisterClassW(&wc);
    RECT parent; GetWindowRect(window, &parent); decisionResult = IDCANCEL;
    HWND dialog = CreateWindowExW(WS_EX_DLGMODALFRAME, wc.lpszClassName,
        L"Datos sin equivalencia directa en CE3X 2.3", WS_POPUP | WS_CAPTION | WS_SYSMENU,
        parent.left + 20, parent.top + 20, 700, 290, window, NULL, wc.hInstance, NULL);
    if (!dialog) return IDCANCEL;
    HWND body = CreateWindowExW(0, L"EDIT", message, WS_CHILD | WS_VISIBLE | WS_TABSTOP | ES_MULTILINE | ES_READONLY | WS_VSCROLL,
        20, 18, 650, 165, dialog, NULL, wc.hInstance, NULL);
    SendMessageW(body, WM_SETFONT, (WPARAM)font, TRUE);
    HWND adapt = CreateWindowExW(0,L"BUTTON",experimental ? L"Adaptar (experimental)" : L"Adaptar y convertir",WS_CHILD | WS_VISIBLE | WS_TABSTOP,
        20,205,190,36,dialog,(HMENU)501,wc.hInstance,NULL);
    HWND omit = CreateWindowExW(0,L"BUTTON",L"Omitir lo indicado y convertir",WS_CHILD | WS_VISIBLE | WS_TABSTOP,
        225,205,230,36,dialog,(HMENU)502,wc.hInstance,NULL);
    HWND cancel = CreateWindowExW(0,L"BUTTON",L"Cancelar",WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_DEFPUSHBUTTON,
        470,205,200,36,dialog,(HMENU)IDCANCEL,wc.hInstance,NULL);
    if (!body || !adapt || !omit || !cancel || GetWindowTextLengthW(body) != wcslen(message)) {
        DestroyWindow(dialog); return IDCANCEL;
    }
    SendMessageW(adapt,WM_SETFONT,(WPARAM)font,TRUE); EnableWindow(adapt,canAdapt);
    SendMessageW(omit,WM_SETFONT,(WPARAM)font,TRUE); SendMessageW(cancel,WM_SETFONT,(WPARAM)font,TRUE);
    EnableWindow(window,FALSE); ShowWindow(dialog,SW_SHOW); SetFocus(cancel);
    if (decisionPreviewPath) {
        RedrawWindow(dialog,NULL,NULL,RDW_INVALIDATE | RDW_UPDATENOW | RDW_ALLCHILDREN);
        decisionPreviewSaved=savePreview(dialog,decisionPreviewPath);
        SendMessageW(dialog,WM_COMMAND,IDCANCEL,0);
    }
    if (decisionSmokeChoice) SendMessageW(dialog,WM_COMMAND,(decisionSmokeChoice==501 && !canAdapt) ? IDCANCEL : decisionSmokeChoice,0);
    MSG msg;
    while (IsWindow(dialog)) {
        int result=GetMessageW(&msg,NULL,0,0);
        if (result<=0) { if (result==0) PostQuitMessage((int)msg.wParam); break; }
        if (!IsDialogMessageW(dialog,&msg)) { TranslateMessage(&msg); DispatchMessageW(&msg); }
    }
    if (IsWindow(dialog)) DestroyWindow(dialog);
    EnableWindow(window,TRUE); SetActiveWindow(window);
    return decisionResult;
}

static void received(void) {
    response[responseSize] = 0;
    char *line = strchr(response, '\n'); if (line) *line = 0;
    char *first = strchr(response, '\t'), *second = first ? strchr(first + 1, '\t') : NULL;
    if (!first || !second) { report(L"El motor devolvio una respuesta inesperada. Comprueba la integridad del paquete."); setBusy(0); return; }
    *first = 0; *second = 0;
    WCHAR path[PATHCAP] = L"";
    static WCHAR message[RESPONSECAP], text[PATHCAP + RESPONSECAP];
    for (char *p = second + 1; *p; p++) {
        if (*p == '\x1e') *p = '\r';
        else if (*p == '\x1f') *p = '\n';
    }
    MultiByteToWideChar(CP_UTF8, 0, first + 1, -1, path, PATHCAP);
    if (!MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, second + 1, -1, message, RESPONSECAP)) {
        report(L"No se pudo mostrar el inventario del motor."); setBusy(0); return;
    }
    int experimental = strcmp(response,"DECISION_EXPERIMENTAL")==0;
    if (operation == 1 && (experimental || strcmp(response,"DECISION_ADAPT")==0 || strcmp(response,"DECISION_OMIT")==0)) {
        if (window) KillTimer(window,1);
        int selected = conversionDecision(message,experimental || strcmp(response,"DECISION_ADAPT")==0,experimental);
        WCHAR json[COMMANDCAP] = L"{\"command\":\"decision\",\"id\":";
        if (!appendJson(json,path)) { setBusy(0); return; }
        wcscat(json,selected==501 ? (experimental ? L",\"choice\":\"experimental\"}" : L",\"choice\":\"adapt\"}") :
            selected==502 ? L",\"choice\":\"omit\"}" : L",\"choice\":\"cancel\"}");
        setBusy(0); request(json,1); return;
    }
    if (operation == 1) {
        if (decisionSmokeChoice) selfTestPassed = strcmp(response,decisionSmokeChoice==IDCANCEL ? "CANCELADO" : "REVISAR_CAMBIOS")==0;
        hasAttempt = 1;
        wcsncpy(lastOutput, path, PATHCAP - 1); lastOutput[PATHCAP - 1] = 0;
        swprintf(text, PATHCAP + RESPONSECAP, L"%ls", strcmp(response, "REVISAR") == 0 ? L"Conversión completada." : message);
    } else if (operation == 2) {
        swprintf(text, PATHCAP + RESPONSECAP, L"%ls\r\n\r\n%ls", message, path);
    } else {
        selfTestPassed = strcmp(response, "OK") == 0;
        swprintf(text, PATHCAP + RESPONSECAP, L"%ls", message);
    }
    report(text); setBusy(0); if (window) KillTimer(window, 1);
}
static void pollEngine(void) {
    if (!busy || !engine.hProcess) return;
    DWORD available = 0, got = 0, code = STILL_ACTIVE;
    if (PeekNamedPipe(engineOutput, NULL, 0, NULL, &available, NULL) && available) {
        DWORD space = RESPONSECAP - responseSize - 1;
        if (!space) { report(L"La respuesta del motor es demasiado larga."); setBusy(0); closeEngine(); return; }
        if (ReadFile(engineOutput, response + responseSize, available < space ? available : space, &got, NULL)) responseSize += got;
        response[responseSize] = 0;
        if (strchr(response, '\n')) { received(); return; }
    }
    if (GetExitCodeProcess(engine.hProcess, &code) && code != STILL_ACTIVE) {
        report(L"El motor se ha cerrado antes de terminar. Comprueba que el ZIP se ha extraido completo.");
        hasAttempt = 0; setBusy(0); closeEngine(); if (window) KillTimer(window, 1);
    }
}
static void chooseSource(void) {
    WCHAR path[PATHCAP] = L""; GetWindowTextW(sourceEdit, path, PATHCAP);
    OPENFILENAMEW dialog = {0}; dialog.lStructSize = sizeof(dialog); dialog.hwndOwner = window;
    dialog.lpstrFile = path; dialog.nMaxFile = PATHCAP;
    dialog.lpstrFilter = L"Proyecto CE3X (*.cex)\0*.cex\0Todos los archivos\0*.*\0";
    dialog.Flags = OFN_FILEMUSTEXIST | OFN_PATHMUSTEXIST | OFN_NOCHANGEDIR;
    if (GetOpenFileNameW(&dialog)) { SetWindowTextW(sourceEdit, path); }
}
static void convert(void) {
    WCHAR source[PATHCAP], output[PATHCAP], json[COMMANDCAP] = L"{\"command\":\"convert\",\"source\":";
    GetWindowTextW(sourceEdit, source, PATHCAP); outputName(source, output);
    if (!exists(source) || !output[0]) { MessageBoxW(window, L"Selecciona un archivo de origen CE3X 3.2 valido.", L"Conversor CE3X", MB_OK | MB_ICONINFORMATION); return; }
    int overwrite = exists(output);
    if (overwrite && MessageBoxW(window, L"Ya existe el archivo _CE3X2.3.cex. Quieres sustituirlo? El original 3.2 se conserva.", L"Confirmar sustitucion", MB_YESNO | MB_DEFBUTTON2 | MB_ICONQUESTION) != IDYES) return;
    if (!appendJson(json, source)) return;
    wcscat(json, overwrite ? L",\"overwrite\":true}" : L",\"overwrite\":false}");
    if (request(json, 1)) { attachedPath[0] = 0; SetWindowTextW(attachmentLabel, L"Sin adjunto"); SetWindowTextW(notesEdit, L""); }
}
static void chooseAttachment(void) {
    WCHAR path[PATHCAP] = L"";
    OPENFILENAMEW dialog = {0}; dialog.lStructSize = sizeof(dialog); dialog.hwndOwner = window;
    dialog.lpstrFile = path; dialog.nMaxFile = PATHCAP;
    dialog.lpstrFilter = L"Logs y capturas\0*.log;*.txt;*.png;*.jpg\0Todos los archivos\0*.*\0";
    dialog.Flags = OFN_FILEMUSTEXIST | OFN_PATHMUSTEXIST | OFN_NOCHANGEDIR;
    if (GetOpenFileNameW(&dialog)) { wcscpy(attachedPath, path); SetWindowTextW(attachmentLabel, path); }
}
static void saveDiagnostic(void) {
    if (!hasAttempt) return;
    WCHAR destination[PATHCAP] = L"CE3X_diagnostico.zip", notes[8192], json[COMMANDCAP] = L"{\"command\":\"diagnostic\",\"destination\":";
    OPENFILENAMEW dialog = {0}; dialog.lStructSize = sizeof(dialog); dialog.hwndOwner = window;
    dialog.lpstrFile = destination; dialog.nMaxFile = PATHCAP; dialog.lpstrDefExt = L"zip";
    dialog.lpstrTitle = L"Guardar diagnostico"; dialog.lpstrFilter = L"Diagnostico ZIP\0*.zip\0";
    dialog.Flags = OFN_OVERWRITEPROMPT | OFN_PATHMUSTEXIST | OFN_NOCHANGEDIR;
    if (!GetSaveFileNameW(&dialog)) return;
    GetWindowTextW(notesEdit, notes, 8192);
    if (!appendJson(json, destination)) return;
    wcscat(json, L",\"notes\":"); if (!appendJson(json, notes)) return;
    if (attachedPath[0]) { wcscat(json, L",\"attachment\":"); if (!appendJson(json, attachedPath)) return; }
    wcscat(json, L",\"overwrite\":true}"); request(json, 2);
}
static int px(int value) { return MulDiv(value, uiDpi, 96); }
static RECT box(int x, int y, int width, int height) {
    RECT result = {px(x), px(y), px(x + width), px(y + height)}; return result;
}
static void fillBox(HDC dc, RECT rect, COLORREF color) {
    HBRUSH brush = CreateSolidBrush(color); FillRect(dc, &rect, brush); DeleteObject(brush);
}
static void frameBox(HDC dc, RECT rect, COLORREF color) {
    HBRUSH brush = CreateSolidBrush(color); FrameRect(dc, &rect, brush); DeleteObject(brush);
}
static HFONT makeFont(int size, int weight) {
    return CreateFontW(-px(size), 0, 0, 0, weight, FALSE, FALSE, FALSE, DEFAULT_CHARSET,
        OUT_DEFAULT_PRECIS, CLIP_DEFAULT_PRECIS, CLEARTYPE_QUALITY, DEFAULT_PITCH | FF_SWISS, L"Segoe UI");
}
static void paintWindow(HDC dc) {
    RECT client; GetClientRect(window, &client); fillBox(dc, client, UI_BACKGROUND);
    fillBox(dc, box(20, 20, 720, 70), UI_HEADER);
    frameBox(dc, box(20, 20, 720, 70), UI_BORDER);
    fillBox(dc, box(20, 108, 720, 64), RGB(255, 255, 255));
    frameBox(dc, box(20, 108, 720, 64), UI_BORDER);
    fillBox(dc, box(20, 244, 720, 1), UI_BORDER);
    int offset = statusVisible ? 80 : 0;
    if (detailsVisible) {
        fillBox(dc, box(20, 304 + offset, 720, 172), RGB(255, 255, 255));
        frameBox(dc, box(20, 304 + offset, 720, 172), UI_BORDER);
    }
}
static void drawButton(const DRAWITEMSTRUCT *item) {
    int primary = item->CtlID == IDC_CONVERT;
    int disabled = (item->itemState & ODS_DISABLED) != 0;
    int pressed = (item->itemState & ODS_SELECTED) != 0;
    COLORREF background = primary ? UI_ACCENT : RGB(250, 251, 253);
    if (pressed) background = primary ? RGB(43, 53, 125) : RGB(227, 231, 240);
    if (disabled) background = primary ? RGB(173, 180, 210) : RGB(239, 241, 245);
    fillBox(item->hDC, item->rcItem, background);
    frameBox(item->hDC, item->rcItem, primary ? background : UI_BORDER);
    SetBkMode(item->hDC, TRANSPARENT);
    SetTextColor(item->hDC, primary ? RGB(255, 255, 255) : (disabled ? RGB(150, 156, 169) : UI_TEXT));
    HFONT old = SelectObject(item->hDC, primary ? strongFont : font);
    WCHAR text[128]; GetWindowTextW(item->hwndItem, text, 128);
    RECT label = item->rcItem;
    if (pressed) OffsetRect(&label, px(1), px(1));
    DrawTextW(item->hDC, text, -1, &label, DT_CENTER | DT_VCENTER | DT_SINGLELINE);
    if ((item->itemState & ODS_FOCUS) && !disabled) {
        RECT focus = item->rcItem; InflateRect(&focus, -px(4), -px(4)); DrawFocusRect(item->hDC, &focus);
    }
    SelectObject(item->hDC, old);
}
static HWND control(const WCHAR *className, const WCHAR *text, DWORD style, int x, int y, int width, int height, int id) {
    if (wcscmp(className, L"STATIC") == 0) style |= SS_NOPREFIX;
    if (wcscmp(className, L"BUTTON") == 0) style = (style & ~BS_TYPEMASK) | BS_OWNERDRAW;
    if (wcscmp(className, L"EDIT") == 0 && id != IDC_REPORT) style |= WS_BORDER;
    HWND item = CreateWindowExW(0, className, text, WS_CHILD | WS_VISIBLE | style,
        px(x), px(y), px(width), px(height), window, (HMENU)(INT_PTR)id, GetModuleHandleW(NULL), NULL);
    SendMessageW(item, WM_SETFONT, (WPARAM)font, TRUE); return item;
}
static void layoutWindow(void) {
    int offset = statusVisible ? 80 : 0;
    MoveWindow(GetDlgItem(window, IDC_NOTICE), px(20), px(260 + offset), px(520), px(26), TRUE);
    MoveWindow(GetDlgItem(window, IDC_DETAILS), px(570), px(258 + offset), px(170), px(30), TRUE);
    int positions[5][4] = {{36, 318, 688, 23}, {36, 348, 688, 54}, {36, 414, 210, 30},
                           {260, 414, 464, 30}, {36, 453, 688, 18}};
    for (int i = 0; i < detailCount; i++)
        MoveWindow(detailControls[i], px(positions[i][0]), px(positions[i][1] + offset),
                   px(positions[i][2]), px(positions[i][3]), TRUE);
    RECT rect = box(0, 0, 760, (detailsVisible ? 496 : 304) + offset);
    AdjustWindowRect(&rect, WS_OVERLAPPED | WS_CAPTION | WS_SYSMENU | WS_MINIMIZEBOX, FALSE);
    SetWindowPos(window, NULL, 0, 0, rect.right - rect.left, rect.bottom - rect.top,
        SWP_NOMOVE | SWP_NOZORDER | SWP_NOACTIVATE);
    InvalidateRect(window, NULL, TRUE);
}
static void toggleDetails(void) {
    detailsVisible = !detailsVisible;
    for (int i = 0; i < detailCount; i++) ShowWindow(detailControls[i], detailsVisible ? SW_SHOW : SW_HIDE);
    SetWindowTextW(GetDlgItem(window, IDC_DETAILS), detailsVisible ? L"- Notas y adjunto" : L"+ Notas y adjunto");
    layoutWindow();
}
static void initializeUI(void) {
    HDC dc = GetDC(window); uiDpi = GetDeviceCaps(dc, LOGPIXELSX); ReleaseDC(window, dc);
    font = makeFont(15, FW_NORMAL); titleFont = makeFont(25, FW_SEMIBOLD);
    strongFont = makeFont(15, FW_SEMIBOLD); smallFont = makeFont(13, FW_NORMAL);
    backgroundBrush = CreateSolidBrush(UI_BACKGROUND); panelBrush = CreateSolidBrush(RGB(255, 255, 255));
    headerBrush = CreateSolidBrush(UI_HEADER);
    HWND title = control(L"STATIC", L"Conversor CE3X 3.2 \x2192 2.3", SS_CENTERIMAGE, 36, 31, 688, 33, IDC_TITLE);
    SendMessageW(title, WM_SETFONT, (WPARAM)titleFont, TRUE);
    HWND version = control(L"STATIC", L"v1.5.3  |  Residencial", 0, 37, 66, 420, 18, IDC_VERSION);
    SendMessageW(version, WM_SETFONT, (WPARAM)smallFont, TRUE);
    control(L"STATIC", L"Archivo de entrada", SS_CENTERIMAGE, 36, 123, 140, 30, IDC_INPUT_LABEL);
    sourceEdit = control(L"EDIT", L"", ES_AUTOHSCROLL | WS_TABSTOP, 182, 123, 403, 30, IDC_SOURCE);
    control(L"BUTTON", L"Examinar...", WS_TABSTOP, 597, 123, 127, 30, IDC_BROWSE);
    convertButton = control(L"BUTTON", L"Convertir", WS_TABSTOP, 20, 192, 190, 40, IDC_CONVERT);
    diagnosticButton = control(L"BUTTON", L"Guardar diagnóstico", WS_TABSTOP, 226, 192, 216, 40, IDC_DIAGNOSTIC);
    openButton = control(L"BUTTON", L"Abrir carpeta", WS_TABSTOP, 458, 192, 188, 40, IDC_OPEN);
    control(L"BUTTON", L"Ayuda", WS_TABSTOP, 662, 192, 78, 40, IDC_HELP);
    reportEdit = control(L"EDIT", L"",
        ES_MULTILINE | ES_READONLY | ES_AUTOVSCROLL | WS_VSCROLL | WS_TABSTOP, 20, 262, 720, 60, IDC_REPORT);
    ShowWindow(reportEdit, SW_HIDE);
    HWND notice = control(L"STATIC", L"Revisa y recalcula el resultado en CE3X 2.3.", SS_CENTERIMAGE, 20, 260, 520, 26, IDC_NOTICE);
    SendMessageW(notice, WM_SETFONT, (WPARAM)smallFont, TRUE);
    control(L"BUTTON", L"+ Notas y adjunto", WS_TABSTOP, 570, 258, 170, 30, IDC_DETAILS);
    detailControls[detailCount++] = control(L"STATIC", L"Información opcional para el diagnóstico", 0, 36, 318, 688, 23, IDC_NOTES_LABEL);
    notesEdit = control(L"EDIT", L"", ES_MULTILINE | ES_AUTOVSCROLL | WS_VSCROLL | WS_TABSTOP, 36, 348, 688, 54, IDC_NOTES);
    detailControls[detailCount++] = notesEdit; SendMessageW(notesEdit, EM_SETLIMITTEXT, 8191, 0);
    detailControls[detailCount++] = control(L"BUTTON", L"Adjuntar log o captura", WS_TABSTOP, 36, 414, 210, 30, IDC_ATTACHMENT);
    attachmentLabel = control(L"STATIC", L"Sin adjunto", SS_PATHELLIPSIS | SS_CENTERIMAGE, 260, 414, 464, 30, IDC_ATTACHMENT_LABEL);
    detailControls[detailCount++] = attachmentLabel;
    HWND retention = control(L"STATIC", L"Guarda el diagnóstico antes de cerrar o convertir otro archivo.", 0, 36, 453, 688, 18, IDC_RETENTION);
    SendMessageW(retention, WM_SETFONT, (WPARAM)smallFont, TRUE); detailControls[detailCount++] = retention;
    for (int i = 0; i < detailCount; i++) ShowWindow(detailControls[i], SW_HIDE);
    setBusy(0); DragAcceptFiles(window, TRUE);
}

// Render the real native window for CI review without invoking the conversion engine.
static int savePreview(HWND target, const WCHAR *path) {
    RECT rect; GetWindowRect(target, &rect);
    int width = rect.right - rect.left, height = rect.bottom - rect.top;
    HDC screen = GetDC(target), memory = CreateCompatibleDC(screen);
    HBITMAP bitmap = CreateCompatibleBitmap(screen, width, height);
    if (!memory || !bitmap) { if (memory) DeleteDC(memory); if (bitmap) DeleteObject(bitmap); ReleaseDC(target, screen); return 0; }
    HGDIOBJ old = SelectObject(memory, bitmap);
    BOOL painted = PrintWindow(target, memory, 0);
    SelectObject(memory, old);
    BITMAPINFO info = {0}; info.bmiHeader.biSize = sizeof(BITMAPINFOHEADER);
    info.bmiHeader.biWidth = width; info.bmiHeader.biHeight = height;
    info.bmiHeader.biPlanes = 1; info.bmiHeader.biBitCount = 32; info.bmiHeader.biCompression = BI_RGB;
    DWORD size = (DWORD)width * (DWORD)height * 4;
    void *pixels = HeapAlloc(GetProcessHeap(), 0, size); int saved = 0;
    if (pixels && painted && GetDIBits(screen, bitmap, 0, height, pixels, &info, DIB_RGB_COLORS)) {
        FILE *file = _wfopen(path, L"wb");
        if (file) {
            BITMAPFILEHEADER header = {0}; header.bfType = 0x4d42;
            header.bfOffBits = sizeof(header) + sizeof(info.bmiHeader); header.bfSize = header.bfOffBits + size;
            saved = fwrite(&header, sizeof(header), 1, file) == 1 &&
                fwrite(&info.bmiHeader, sizeof(info.bmiHeader), 1, file) == 1 && fwrite(pixels, size, 1, file) == 1;
            fclose(file);
        }
    }
    if (pixels) HeapFree(GetProcessHeap(), 0, pixels);
    DeleteObject(bitmap); DeleteDC(memory); ReleaseDC(target, screen); return saved;
}

static LRESULT CALLBACK windowProc(HWND hwnd, UINT message, WPARAM wp, LPARAM lp) {
    switch (message) {
    case WM_CREATE: window = hwnd; initializeUI(); return 0;
    case WM_COMMAND:
        if (LOWORD(wp) == IDC_SOURCE && HIWORD(wp) == EN_CHANGE) { return 0; }
        if (busy) return 0;
        switch (LOWORD(wp)) {
        case IDC_BROWSE: chooseSource(); break;
        case IDC_CONVERT: convert(); break;
        case IDC_DIAGNOSTIC: saveDiagnostic(); break;
        case IDC_ATTACHMENT: chooseAttachment(); break;
        case IDC_OPEN: if (lastOutput[0]) {
            WCHAR folder[PATHCAP]; wcscpy(folder, lastOutput); WCHAR *slash = wcsrchr(folder, L'\\'); if (slash) *slash = 0;
            ShellExecuteW(hwnd, L"open", folder, NULL, NULL, SW_SHOWNORMAL);
        } break;
        case IDC_DETAILS: toggleDetails(); break;
        case IDC_HELP: MessageBoxW(hwnd, L"1. Selecciona el CEX 3.2.\r\n2. Pulsa Convertir.\r\n3. Abre nombre_CE3X2.3.cex junto al original.\r\n4. Revisa y recalcula en CE3X 2.3.\r\n\r\nSi aparece un error, guarda el diagnostico antes de cerrar el programa o hacer otra conversion. No se generan logs automaticamente.", L"Instrucciones", MB_OK); break;
        } return 0;
    case WM_PAINT: {
        PAINTSTRUCT paint; HDC dc = BeginPaint(hwnd, &paint); paintWindow(dc); EndPaint(hwnd, &paint); return 0;
    }
    case WM_PRINTCLIENT: paintWindow((HDC)wp); return 0;
    case WM_DRAWITEM: drawButton((const DRAWITEMSTRUCT *)lp); return TRUE;
    case WM_CTLCOLORSTATIC: {
        HDC dc = (HDC)wp; int id = GetDlgCtrlID((HWND)lp);
        COLORREF background = UI_BACKGROUND; HBRUSH brush = backgroundBrush;
        if (id == IDC_TITLE || id == IDC_VERSION) { background = UI_HEADER; brush = headerBrush; }
        else if ((id >= IDC_INPUT_LABEL && id <= IDC_OUTPUT_HELP) || id == IDC_NOTES_LABEL || id == IDC_ATTACHMENT_LABEL || id == IDC_RETENTION) {
            background = RGB(255, 255, 255); brush = panelBrush;
        }
        SetTextColor(dc, (id == IDC_VERSION || id == IDC_OUTPUT_HELP || id == IDC_NOTICE || id == IDC_RETENTION) ? RGB(91, 100, 118) : UI_TEXT);
        SetBkColor(dc, background); return (LRESULT)brush;
    }
    case WM_CTLCOLOREDIT: SetTextColor((HDC)wp, UI_TEXT); SetBkColor((HDC)wp, RGB(255, 255, 255)); return (LRESULT)panelBrush;
    case DM_GETDEFID: return MAKELONG(IDC_CONVERT, DC_HASDEFID);
    case WM_TIMER: pollEngine(); return 0;
    case WM_DROPFILES: {
        HDROP drop = (HDROP)wp; WCHAR path[PATHCAP];
        if (!busy && DragQueryFileW(drop, 0, path, PATHCAP)) { SetWindowTextW(sourceEdit, path); }
        DragFinish(drop); return 0;
    }
    case WM_CLOSE:
        if (busy) { MessageBoxW(hwnd, L"Espera a que termine la operacion.", L"Conversor CE3X", MB_OK); return 0; }
        DestroyWindow(hwnd); return 0;
    case WM_DESTROY:
        closeEngine();
        if (font) DeleteObject(font); if (titleFont) DeleteObject(titleFont);
        if (strongFont) DeleteObject(strongFont); if (smallFont) DeleteObject(smallFont);
        if (backgroundBrush) DeleteObject(backgroundBrush); if (panelBrush) DeleteObject(panelBrush); if (headerBrush) DeleteObject(headerBrush);
        PostQuitMessage(0); return 0;
    }
    return DefWindowProcW(hwnd, message, wp, lp);
}
int WINAPI wWinMain(HINSTANCE instance, HINSTANCE previous, PWSTR commandLine, int show) {
    (void)previous; (void)commandLine;
    SetProcessDPIAware();
    HDC desktop = GetDC(NULL); uiDpi = GetDeviceCaps(desktop, LOGPIXELSX); ReleaseDC(NULL, desktop);
    GetModuleFileNameW(NULL, baseDir, PATHCAP);
    WCHAR *slash = wcsrchr(baseDir, L'\\'); if (slash) *slash = 0;
    int argc; WCHAR **argv = CommandLineToArgvW(GetCommandLineW(), &argc);
    if (argc >= 2 && wcscmp(argv[1], L"--self-test") == 0) {
        if (request(L"{\"command\":\"self-test\"}", 3)) {
            ULONGLONG started = GetTickCount64();
            while (busy && GetTickCount64() - started < 30000) { pollEngine(); Sleep(10); }
        }
        if (argc >= 3) {
            FILE *file = _wfopen(argv[2], L"wb");
            if (file) { fputs(selfTestPassed ? "OK\n" : "ERROR\n", file); fclose(file); }
        }
        closeEngine(); LocalFree(argv); return selfTestPassed ? 0 : 1;
    }
    WNDCLASSW wc = {0}; wc.lpfnWndProc = windowProc; wc.hInstance = instance;
    wc.lpszClassName = L"CE3XConversorWindow"; wc.hCursor = LoadCursor(NULL, IDC_ARROW);
    wc.hbrBackground = NULL; wc.hIcon = LoadIcon(NULL, IDI_APPLICATION);
    RegisterClassW(&wc);
    RECT rect = box(0, 0, 760, 304);
    DWORD style = WS_OVERLAPPED | WS_CAPTION | WS_SYSMENU | WS_MINIMIZEBOX;
    AdjustWindowRect(&rect, style, FALSE);
    window = CreateWindowW(wc.lpszClassName, L"Conversor CE3X 3.2 \x2192 2.3", style, CW_USEDEFAULT, CW_USEDEFAULT,
        rect.right - rect.left, rect.bottom - rect.top, NULL, NULL, instance, NULL);
    if (!window) { LocalFree(argv); return 1; }
    if (argc >= 5 && wcscmp(argv[1], L"--smoke-decision") == 0) {
        decisionSmokeChoice = wcscmp(argv[3],L"adapt")==0 ? 501 : wcscmp(argv[3],L"omit")==0 ? 502 : IDCANCEL;
        SetWindowTextW(sourceEdit,argv[2]); ShowWindow(window,SW_SHOWNORMAL); UpdateWindow(window); convert();
        ULONGLONG started=GetTickCount64(); MSG testMessage;
        while (busy && GetTickCount64()-started<30000) {
            while (PeekMessageW(&testMessage,NULL,0,0,PM_REMOVE)) { TranslateMessage(&testMessage); DispatchMessageW(&testMessage); }
            pollEngine(); Sleep(10);
        }
        FILE *file=_wfopen(argv[4],L"wb");
        if (file) { fputs(selfTestPassed ? "OK\n" : "ERROR\n",file); fclose(file); }
        DestroyWindow(window); LocalFree(argv); return selfTestPassed ? 0 : 1;
    }
    if (argc >= 3 && wcscmp(argv[1], L"--preview-decision") == 0) {
        decisionPreviewPath=argv[2]; ShowWindow(window,SW_SHOWNORMAL); UpdateWindow(window);
        conversionDecision(L"Edificio: SOLAR_MENSUAL. Produccion 1413.258 kWh/ano. Se propone cobertura ACS 70 %. Se pierden reparto mensual y potencia solar. Omitir elimina esta instalacion. Revisar y recalcular en CE3X 2.3.", argc < 4 || wcscmp(argv[3],L"omit") != 0,0);
        DestroyWindow(window); LocalFree(argv); return decisionPreviewSaved ? 0 : 1;
    }
    if (argc >= 3 && wcscmp(argv[1], L"--preview") == 0) {
        SetWindowTextW(sourceEdit, L"C:\\Proyectos\\Vivienda.cex");
        ShowWindow(window, SW_SHOWNORMAL); UpdateWindow(window);
        int saved = savePreview(window,argv[2]); DestroyWindow(window); LocalFree(argv); return saved ? 0 : 1;
    }
    if (argc >= 2) { SetWindowTextW(sourceEdit, argv[1]); }
    LocalFree(argv); ShowWindow(window, show); UpdateWindow(window);
    MSG message;
    while (GetMessageW(&message, NULL, 0, 0) > 0) {
        if (!IsDialogMessageW(window, &message)) { TranslateMessage(&message); DispatchMessageW(&message); }
    }
    return (int)message.wParam;
}
