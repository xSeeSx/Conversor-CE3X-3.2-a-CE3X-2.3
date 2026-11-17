#define UNICODE
#define _UNICODE
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <commdlg.h>
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

static HWND window, sourceEdit, outputLabel, convertButton, diagnosticButton, openButton, notesEdit, reportEdit, attachmentLabel;
static HFONT font;
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
    if (reportEdit) SetWindowTextW(reportEdit, lastReport);
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
    WCHAR *slash = wcsrchr(output, L'\\'), *dot = wcsrchr(output, L'.');
    if (dot && (!slash || dot > slash)) *dot = 0;
    if (wcslen(output) + 13 < PATHCAP) wcscat(output, L"_CE3X2.3.cex");
    else output[0] = 0;
}
static void updateOutput(void) {
    WCHAR source[PATHCAP], output[PATHCAP];
    GetWindowTextW(sourceEdit, source, PATHCAP);
    outputName(source, output);
    SetWindowTextW(outputLabel, source[0] ? output : L"Se guardara junto al original como nombre_CE3X2.3.cex");
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
static void received(void) {
    response[responseSize] = 0;
    char *line = strchr(response, '\n'); if (line) *line = 0;
    char *first = strchr(response, '\t'), *second = first ? strchr(first + 1, '\t') : NULL;
    if (!first || !second) { report(L"El motor devolvio una respuesta inesperada. Comprueba la integridad del paquete."); setBusy(0); return; }
    *first = 0; *second = 0;
    WCHAR path[PATHCAP] = L"", message[8192] = L"", text[PATHCAP + 8192];
    MultiByteToWideChar(CP_UTF8, 0, first + 1, -1, path, PATHCAP);
    MultiByteToWideChar(CP_UTF8, 0, second + 1, -1, message, 8192);
    if (operation == 1) {
        hasAttempt = 1;
        wcsncpy(lastOutput, path, PATHCAP - 1); lastOutput[PATHCAP - 1] = 0;
        swprintf(text, PATHCAP + 8192, L"%ls\r\n\r\n%ls\r\n\r\nSi aparece un error, pulsa Guardar diagnostico. La informacion se conserva en memoria hasta cerrar el programa o hacer otra conversion.", message, path);
    } else if (operation == 2) {
        swprintf(text, PATHCAP + 8192, L"%ls\r\n\r\n%ls", message, path);
    } else {
        selfTestPassed = strcmp(response, "OK") == 0;
        swprintf(text, PATHCAP + 8192, L"%ls", message);
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
    if (GetOpenFileNameW(&dialog)) { SetWindowTextW(sourceEdit, path); updateOutput(); }
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
static HWND control(const WCHAR *className, const WCHAR *text, DWORD style, int x, int y, int width, int height, int id) {
    HWND item = CreateWindowExW(wcscmp(className, L"EDIT") == 0 ? WS_EX_CLIENTEDGE : 0, className, text,
        WS_CHILD | WS_VISIBLE | style, x, y, width, height, window, (HMENU)(INT_PTR)id, GetModuleHandleW(NULL), NULL);
    SendMessageW(item, WM_SETFONT, (WPARAM)font, TRUE); return item;
}
static void initializeUI(void) {
    font = CreateFontW(-16, 0, 0, 0, FW_NORMAL, FALSE, FALSE, FALSE, DEFAULT_CHARSET,
        OUT_DEFAULT_PRECIS, CLIP_DEFAULT_PRECIS, DEFAULT_QUALITY, DEFAULT_PITCH, L"Segoe UI");
    control(L"STATIC", L"Conversor CE3X 3.2 a 2.3", 0, 24, 20, 700, 28, 0);
    control(L"STATIC", L"Version 1.4.0 | Residencial | Conversion experimental", 0, 24, 55, 800, 24, 0);
    control(L"STATIC", L"Archivo de origen CE3X 3.2", 0, 24, 100, 750, 24, 0);
    sourceEdit = control(L"EDIT", L"", ES_AUTOHSCROLL | WS_TABSTOP, 24, 130, 660, 30, IDC_SOURCE);
    control(L"BUTTON", L"Examinar...", WS_TABSTOP, 700, 130, 135, 30, IDC_BROWSE);
    control(L"STATIC", L"Archivo de salida", 0, 24, 182, 750, 24, 0);
    outputLabel = control(L"STATIC", L"Se guardara junto al original como nombre_CE3X2.3.cex", SS_PATHELLIPSIS, 24, 212, 810, 40, 0);
    convertButton = control(L"BUTTON", L"Convertir", BS_DEFPUSHBUTTON | WS_TABSTOP, 24, 272, 235, 40, IDC_CONVERT);
    openButton = control(L"BUTTON", L"Abrir carpeta del archivo", WS_TABSTOP, 275, 272, 270, 40, IDC_OPEN);
    control(L"BUTTON", L"Instrucciones", WS_TABSTOP, 700, 272, 135, 40, IDC_HELP);
    reportEdit = control(L"EDIT", L"Selecciona o arrastra un archivo .cex.\r\nSe conserva el original. Revisa y recalcula el resultado en CE3X 2.3.\r\nLos logs solo se guardan cuando lo solicitas.", ES_MULTILINE | ES_READONLY | ES_AUTOVSCROLL | WS_VSCROLL | WS_TABSTOP, 24, 340, 810, 145, 0);
    control(L"STATIC", L"Si aparece un error, describe que estabas haciendo (opcional)", 0, 24, 510, 800, 24, 0);
    notesEdit = control(L"EDIT", L"", ES_MULTILINE | ES_AUTOVSCROLL | WS_VSCROLL | WS_TABSTOP, 24, 540, 810, 70, IDC_NOTES);
    SendMessageW(notesEdit, EM_SETLIMITTEXT, 8191, 0);
    control(L"BUTTON", L"Adjuntar log o captura...", WS_TABSTOP, 24, 625, 235, 35, IDC_ATTACHMENT);
    attachmentLabel = control(L"STATIC", L"Sin adjunto", SS_PATHELLIPSIS, 275, 631, 555, 25, 0);
    diagnosticButton = control(L"BUTTON", L"Guardar diagnostico...", WS_TABSTOP, 24, 680, 235, 40, IDC_DIAGNOSTIC);
    control(L"STATIC", L"Solo se crea un ZIP al pulsar el boton.\r\nRevisalo antes de compartirlo.", 0, 275, 680, 550, 45, 0);
    setBusy(0); DragAcceptFiles(window, TRUE);
}
static LRESULT CALLBACK windowProc(HWND hwnd, UINT message, WPARAM wp, LPARAM lp) {
    switch (message) {
    case WM_CREATE: window = hwnd; initializeUI(); return 0;
    case WM_COMMAND:
        if (LOWORD(wp) == IDC_SOURCE && HIWORD(wp) == EN_CHANGE) { updateOutput(); return 0; }
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
        case IDC_HELP: MessageBoxW(hwnd, L"1. Selecciona el CEX 3.2.\r\n2. Pulsa Convertir.\r\n3. Abre nombre_CE3X2.3.cex junto al original.\r\n4. Revisa y recalcula en CE3X 2.3.\r\n\r\nSi aparece un error, guarda el diagnostico antes de cerrar el programa o hacer otra conversion. No se generan logs automaticamente.", L"Instrucciones", MB_OK); break;
        } return 0;
    case WM_TIMER: pollEngine(); return 0;
    case WM_DROPFILES: {
        HDROP drop = (HDROP)wp; WCHAR path[PATHCAP];
        if (!busy && DragQueryFileW(drop, 0, path, PATHCAP)) { SetWindowTextW(sourceEdit, path); updateOutput(); }
        DragFinish(drop); return 0;
    }
    case WM_CLOSE:
        if (busy) { MessageBoxW(hwnd, L"Espera a que termine la operacion.", L"Conversor CE3X", MB_OK); return 0; }
        DestroyWindow(hwnd); return 0;
    case WM_DESTROY: closeEngine(); if (font) DeleteObject(font); PostQuitMessage(0); return 0;
    }
    return DefWindowProcW(hwnd, message, wp, lp);
}
int WINAPI wWinMain(HINSTANCE instance, HINSTANCE previous, PWSTR commandLine, int show) {
    (void)previous; (void)commandLine;
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
    wc.hbrBackground = (HBRUSH)(COLOR_BTNFACE + 1); wc.hIcon = LoadIcon(NULL, IDI_APPLICATION);
    RegisterClassW(&wc);
    RECT rect = {0, 0, 860, 750};
    DWORD style = WS_OVERLAPPED | WS_CAPTION | WS_SYSMENU | WS_MINIMIZEBOX;
    AdjustWindowRect(&rect, style, FALSE);
    window = CreateWindowW(wc.lpszClassName, L"Conversor CE3X 3.2 a 2.3", style, CW_USEDEFAULT, CW_USEDEFAULT,
        rect.right - rect.left, rect.bottom - rect.top, NULL, NULL, instance, NULL);
    if (!window) { LocalFree(argv); return 1; }
    if (argc >= 2) { SetWindowTextW(sourceEdit, argv[1]); updateOutput(); }
    LocalFree(argv); ShowWindow(window, show); UpdateWindow(window);
    MSG message;
    while (GetMessageW(&message, NULL, 0, 0) > 0) {
        if (!IsDialogMessageW(window, &message)) { TranslateMessage(&message); DispatchMessageW(&message); }
    }
    return (int)message.wParam;
}
