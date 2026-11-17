#define UNICODE
#define _UNICODE
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <commdlg.h>
#include <shlobj.h>
#include <shellapi.h>
#include <stdio.h>
#include <wchar.h>

#define PATHCAP 32768
#define IDC_SOURCE 101
#define IDC_TEMPLATE 102
#define IDC_OUTPUT 103
#define IDC_CONVERT 104
#define IDC_OPEN 105
#define IDC_EVIDENCE 106
#define IDC_REPORT 108
#define IDC_NOTES 109
#define IDC_README 110
#define IDC_RESUME 111

static HWND mainWindow, sourceEdit, templateEdit, outEdit, reportEdit, notesEdit, convertButton, evidenceButton, openButton;
static HFONT font;
static WCHAR baseDir[PATHCAP], bridgePath[PATHCAP], bootPath[PATHCAP], notesPath[PATHCAP], lastRun[PATHCAP];
static PROCESS_INFORMATION process;
static int running = 0;

static void setReport(const WCHAR *text) { SetWindowTextW(reportEdit, text); }
static HWND control(DWORD ex, const WCHAR *cls, const WCHAR *text, DWORD style, int x, int y, int w, int h, int id) {
    HWND hwnd=CreateWindowExW(ex,cls,text,WS_CHILD|WS_VISIBLE|style,x,y,w,h,mainWindow,(HMENU)(INT_PTR)id,GetModuleHandleW(NULL),NULL);
    SendMessageW(hwnd,WM_SETFONT,(WPARAM)font,TRUE); return hwnd;
}
static int exists(const WCHAR *path) { DWORD a=GetFileAttributesW(path); return a!=INVALID_FILE_ATTRIBUTES && !(a & FILE_ATTRIBUTE_DIRECTORY); }
static void systemError(const WCHAR *context) {
    DWORD code=GetLastError(); WCHAR err[1024],msg[1500];
    FormatMessageW(FORMAT_MESSAGE_FROM_SYSTEM|FORMAT_MESSAGE_IGNORE_INSERTS,NULL,code,0,err,1024,NULL);
    swprintf(msg,1500,L"%ls\r\nCodigo Windows %lu: %ls",context,(unsigned long)code,err);
    MessageBoxW(mainWindow,msg,L"Conversor CE3X",MB_OK|MB_ICONERROR);
}
static int browseFile(HWND edit, BOOL any) {
    WCHAR path[PATHCAP]=L""; GetWindowTextW(edit,path,PATHCAP);
    OPENFILENAMEW ofn={0};ofn.lStructSize=sizeof(ofn);ofn.hwndOwner=mainWindow;
    ofn.lpstrFile=path;ofn.nMaxFile=PATHCAP;
    ofn.lpstrFilter=any?L"Logs y adjuntos\0*.log;*.txt;*.png;*.jpg;*.cex\0Todos los archivos\0*.*\0":L"Proyecto CE3X (*.cex)\0*.cex\0Todos los archivos\0*.*\0";
    ofn.Flags=OFN_FILEMUSTEXIST|OFN_PATHMUSTEXIST|OFN_NOCHANGEDIR;
    if(GetOpenFileNameW(&ofn)){SetWindowTextW(edit,path);return 1;}return 0;
}
static int chooseAttachment(WCHAR *path) {
    path[0]=0;OPENFILENAMEW ofn={0};ofn.lStructSize=sizeof(ofn);ofn.hwndOwner=mainWindow;
    ofn.lpstrFile=path;ofn.nMaxFile=PATHCAP;ofn.lpstrTitle=L"Adjuntar log de CE3X o captura (Cancelar permite guardar solo las notas)";
    ofn.lpstrFilter=L"Logs, capturas y proyectos\0*.log;*.txt;*.png;*.jpg;*.cex\0Todos los archivos\0*.*\0";
    ofn.Flags=OFN_FILEMUSTEXIST|OFN_PATHMUSTEXIST|OFN_NOCHANGEDIR;
    return GetOpenFileNameW(&ofn)!=0;
}
static void browseFolder(void) {
    BROWSEINFOW bi={0};bi.hwndOwner=mainWindow;bi.lpszTitle=L"Carpeta para los intentos y los diagnosticos";
    bi.ulFlags=BIF_RETURNONLYFSDIRS|BIF_NEWDIALOGSTYLE;
    PIDLIST_ABSOLUTE pidl=SHBrowseForFolderW(&bi);
    if(pidl){WCHAR path[MAX_PATH];if(SHGetPathFromIDListW(pidl,path))SetWindowTextW(outEdit,path);CoTaskMemFree(pidl);}
}
// Quoting for CommandLineToArgvW rules; CreateProcessW never invokes a shell.
static int addArg(WCHAR *cmd, size_t cap, const WCHAR *value) {
    size_t n=wcslen(cmd);if(n+4>=cap)return 0;cmd[n++]=L' ';cmd[n++]=L'"';
    const WCHAR *p=value;
    while(*p){
        size_t slashes=0;while(*p==L'\\'){slashes++;p++;}
        if(*p==L'"'){
            if(n+2*slashes+3>=cap)return 0;
            for(size_t i=0;i<2*slashes+1;i++)cmd[n++]=L'\\';cmd[n++]=*p++;
        }else if(!*p){
            if(n+2*slashes+3>=cap)return 0;
            for(size_t i=0;i<2*slashes;i++)cmd[n++]=L'\\';break;
        }else{
            if(n+slashes+3>=cap)return 0;
            for(size_t i=0;i<slashes;i++)cmd[n++]=L'\\';cmd[n++]=*p++;
        }
    }
    cmd[n++]=L'"';cmd[n]=0;return 1;
}
static void setBusy(int value){
    running=value;EnableWindow(convertButton,!value);EnableWindow(evidenceButton,!value&&lastRun[0]);EnableWindow(openButton,lastRun[0]!=0);
}
static WCHAR *readUtf8(const WCHAR *path) {
    HANDLE f=CreateFileW(path,GENERIC_READ,FILE_SHARE_READ|FILE_SHARE_WRITE,NULL,OPEN_EXISTING,FILE_ATTRIBUTE_NORMAL,NULL);
    if(f==INVALID_HANDLE_VALUE)return NULL;
    DWORD size=GetFileSize(f,NULL);if(size==INVALID_FILE_SIZE||size>4*1024*1024){CloseHandle(f);return NULL;}
    char *bytes=HeapAlloc(GetProcessHeap(),0,size+1);DWORD got=0;
    if(!bytes){CloseHandle(f);return NULL;}
    ReadFile(f,bytes,size,&got,NULL);CloseHandle(f);bytes[got]=0;
    int count=MultiByteToWideChar(CP_UTF8,0,bytes,got,NULL,0);
    WCHAR *result=HeapAlloc(GetProcessHeap(),HEAP_ZERO_MEMORY,(count+1)*sizeof(WCHAR));
    if(result)MultiByteToWideChar(CP_UTF8,0,bytes,got,result,count);
    HeapFree(GetProcessHeap(),0,bytes);return result;
}
static void finishProcess(void) {
    DWORD code=1;GetExitCodeProcess(process.hProcess,&code);CloseHandle(process.hProcess);CloseHandle(process.hThread);
    WCHAR *data=readUtf8(bridgePath);
    if(data){
        WCHAR *first=wcschr(data,L'\n');WCHAR *second=first?wcschr(first+1,L'\n'):NULL;
        if(first&&second){
            *first=0;*second=0;
            if(first[1]){wcsncpy(lastRun,first+1,PATHCAP-1);lastRun[PATHCAP-1]=0;}else{lastRun[0]=0;}
            WCHAR msg[PATHCAP+4000];
            swprintf(msg,PATHCAP+4000,L"Estado: %ls\r\n\r\n%ls\r\n\r\nCarpeta del intento:\r\n%ls\r\n\r\nEl ZIP de diagnostico se guarda junto a esa carpeta.\r\nSi CE3X falla, escribe la accion y el elemento y pulsa Guardar error / adjunto.",data,second+1,lastRun);
            setReport(msg);
        }else setReport(data);
        HeapFree(GetProcessHeap(),0,data);
    }else{
        WCHAR *boot=readUtf8(bootPath);WCHAR msg[10000];
        swprintf(msg,10000,L"El motor termino con codigo %lu sin resultado.\r\nLog de arranque: %ls\r\n\r\n%ls",(unsigned long)code,bootPath,boot?boot:L"No se pudo leer el log. Comprueba que has extraido todo el ZIP.");
        setReport(msg);if(boot)HeapFree(GetProcessHeap(),0,boot);
    }
    DeleteFileW(notesPath);setBusy(0);
}
static int startEngine(const WCHAR **args,int count,BOOL hidden) {
    WCHAR python[PATHCAP],script[PATHCAP],command[32768];
    swprintf(python,PATHCAP,L"%ls\\runtime\\python.exe",baseDir);
    swprintf(script,PATHCAP,L"%ls\\app\\converter.py",baseDir);
    if(!exists(python)||!exists(script)){
        MessageBoxW(mainWindow,L"Falta el motor. Extrae todo el ZIP y abre Conversor_CE3X.exe dentro de su carpeta.",L"Conversor CE3X",MB_OK|MB_ICONERROR);return 0;
    }
    DeleteFileW(bridgePath);command[0]=0;
    const WCHAR *initial[]={python,L"-I",script};
    for(int i=0;i<3;i++)if(!addArg(command,32768,initial[i]))return 0;
    for(int i=0;i<count;i++)if(!addArg(command,32768,args[i])){
        MessageBoxW(mainWindow,L"Las rutas son demasiado largas para Windows.",L"Conversor CE3X",MB_OK|MB_ICONERROR);return 0;
    }
    if(!addArg(command,32768,L"--bridge")||!addArg(command,32768,bridgePath))return 0;
    SECURITY_ATTRIBUTES sa={sizeof(sa),NULL,TRUE};
    HANDLE log=CreateFileW(bootPath,GENERIC_WRITE,FILE_SHARE_READ|FILE_SHARE_WRITE,&sa,CREATE_ALWAYS,FILE_ATTRIBUTE_NORMAL,NULL);
    if(log==INVALID_HANDLE_VALUE){systemError(L"No se pudo crear el log de arranque");return 0;}
    STARTUPINFOW si={0};si.cb=sizeof(si);si.dwFlags=STARTF_USESTDHANDLES|STARTF_USESHOWWINDOW;
    si.wShowWindow=hidden?SW_HIDE:SW_SHOW;si.hStdOutput=log;si.hStdError=log;
    si.hStdInput=CreateFileW(L"NUL",GENERIC_READ,FILE_SHARE_READ|FILE_SHARE_WRITE,&sa,OPEN_EXISTING,0,NULL);
    ZeroMemory(&process,sizeof(process));
    BOOL ok=CreateProcessW(python,command+1,NULL,NULL,TRUE,CREATE_NO_WINDOW,NULL,baseDir,&si,&process);
    CloseHandle(log);if(si.hStdInput!=INVALID_HANDLE_VALUE)CloseHandle(si.hStdInput);
    if(!ok){systemError(L"No se pudo iniciar el motor de conversion");return 0;}
    setBusy(1);setReport(L"Procesando. Se estan leyendo y validando los bloques del archivo...\r\nCada intento se conserva en una carpeta independiente.");SetTimer(mainWindow,1,150,NULL);return 1;
}
static void convert(void){
    WCHAR source[PATHCAP],templ[PATHCAP],output[PATHCAP];
    GetWindowTextW(sourceEdit,source,PATHCAP);GetWindowTextW(templateEdit,templ,PATHCAP);GetWindowTextW(outEdit,output,PATHCAP);
    if(!exists(source)||!exists(templ)||!output[0]){MessageBoxW(mainWindow,L"Selecciona un archivo 3.2, una plantilla 2.3 y una carpeta de resultados.",L"Conversor CE3X",MB_OK|MB_ICONINFORMATION);return;}
    const WCHAR *args[]={L"convert",L"--source",source,L"--template",templ,L"--outdir",output};
    startEngine(args,7,TRUE);
}
static int writeNotes(void){
    int len=GetWindowTextLengthW(notesEdit);WCHAR *notes=HeapAlloc(GetProcessHeap(),HEAP_ZERO_MEMORY,(len+1)*sizeof(WCHAR));
    if(!notes)return 0;GetWindowTextW(notesEdit,notes,len+1);
    int bytes=WideCharToMultiByte(CP_UTF8,0,notes,len,NULL,0,NULL,NULL);
    char *utf=HeapAlloc(GetProcessHeap(),0,bytes+1);if(!utf){HeapFree(GetProcessHeap(),0,notes);return 0;}
    WideCharToMultiByte(CP_UTF8,0,notes,len,utf,bytes,NULL,NULL);HeapFree(GetProcessHeap(),0,notes);
    HANDLE f=CreateFileW(notesPath,GENERIC_WRITE,0,NULL,CREATE_ALWAYS,FILE_ATTRIBUTE_NORMAL,NULL);
    if(f==INVALID_HANDLE_VALUE){HeapFree(GetProcessHeap(),0,utf);return 0;}
    DWORD written;BOOL ok=WriteFile(f,utf,bytes,&written,NULL);CloseHandle(f);HeapFree(GetProcessHeap(),0,utf);return ok;
}
static void attachEvidence(void){
    if(!lastRun[0])return;
    WCHAR attached[PATHCAP];BOOL has=chooseAttachment(attached);
    if(!has&&GetWindowTextLengthW(notesEdit)==0)return;
    if(!writeNotes()){systemError(L"No se pudieron guardar las notas");return;}
    const WCHAR *args[]={L"evidence",L"--run",lastRun,L"--notes-file",notesPath,L"--log",attached};
    startEngine(args,has?7:5,TRUE);
}
static void resumeRun(void){
    BROWSEINFOW bi={0};bi.hwndOwner=mainWindow;bi.lpszTitle=L"Selecciona la carpeta intento_... que contiene resultado.json";
    bi.ulFlags=BIF_RETURNONLYFSDIRS|BIF_NEWDIALOGSTYLE;
    PIDLIST_ABSOLUTE pidl=SHBrowseForFolderW(&bi);
    if(pidl){
        WCHAR path[MAX_PATH],manifest[PATHCAP];
        if(SHGetPathFromIDListW(pidl,path)){
            swprintf(manifest,PATHCAP,L"%ls\\resultado.json",path);
            if(exists(manifest)){
                wcsncpy(lastRun,path,PATHCAP-1);lastRun[PATHCAP-1]=0;
                setBusy(0);setReport(L"Intento anterior seleccionado. Escribe el error de CE3X y pulsa Guardar error / adjunto. El ZIP de diagnostico se actualizara junto a la carpeta del intento.");
            }else MessageBoxW(mainWindow,L"La carpeta seleccionada no contiene resultado.json.",L"Conversor CE3X",MB_OK|MB_ICONINFORMATION);
        }
        CoTaskMemFree(pidl);
    }
}
static void initializeUI(void){
    font=CreateFontW(-16,0,0,0,FW_NORMAL,FALSE,FALSE,FALSE,DEFAULT_CHARSET,OUT_DEFAULT_PRECIS,CLIP_DEFAULT_PRECIS,DEFAULT_QUALITY,DEFAULT_PITCH,L"Segoe UI");
    control(0,L"STATIC",L"Conversor CE3X 3.2 a 2.3",0,24,16,700,28,0);
    control(0,L"STATIC",L"Residencial | Version 1.3.0 | Conversion experimental con diagnostico local",0,24,47,850,23,0);
    control(0,L"STATIC",L"1. Archivo de origen CE3X 3.2",0,24,84,780,22,0);
    sourceEdit=control(WS_EX_CLIENTEDGE,L"EDIT",L"",ES_AUTOHSCROLL|WS_TABSTOP,24,108,745,29,IDC_SOURCE);
    control(0,L"BUTTON",L"Examinar...",BS_PUSHBUTTON|WS_TABSTOP,781,108,115,29,201);
    control(0,L"STATIC",L"2. Plantilla nativa 2.3, solo se usa como referencia de estructura",0,24,151,850,22,0);
    WCHAR templ[PATHCAP];swprintf(templ,PATHCAP,L"%ls\\app\\plantilla_23.cex",baseDir);
    templateEdit=control(WS_EX_CLIENTEDGE,L"EDIT",templ,ES_AUTOHSCROLL|WS_TABSTOP,24,175,745,29,IDC_TEMPLATE);
    control(0,L"BUTTON",L"Cambiar...",BS_PUSHBUTTON|WS_TABSTOP,781,175,115,29,202);
    control(0,L"STATIC",L"3. Carpeta de resultados, un intento nuevo cada vez",0,24,218,850,22,0);
    WCHAR documents[MAX_PATH],dest[PATHCAP];SHGetFolderPathW(NULL,CSIDL_PERSONAL,NULL,SHGFP_TYPE_CURRENT,documents);swprintf(dest,PATHCAP,L"%ls\\CE3X_conversiones",documents);
    outEdit=control(WS_EX_CLIENTEDGE,L"EDIT",dest,ES_AUTOHSCROLL|WS_TABSTOP,24,242,745,29,IDC_OUTPUT);
    control(0,L"BUTTON",L"Cambiar...",BS_PUSHBUTTON|WS_TABSTOP,781,242,115,29,203);
    control(0,L"STATIC",L"Acentos y ene con tilde: reparacion automatica. Se convierten los conjuntos de mejora.",0,24,284,870,27,0);
    convertButton=control(0,L"BUTTON",L"Convertir y generar diagnostico",BS_DEFPUSHBUTTON|WS_TABSTOP,24,325,310,39,IDC_CONVERT);
    openButton=control(0,L"BUTTON",L"Abrir carpeta del intento",BS_PUSHBUTTON|WS_TABSTOP,346,325,260,39,IDC_OPEN);
    control(0,L"BUTTON",L"Instrucciones",BS_PUSHBUTTON|WS_TABSTOP,620,325,128,39,IDC_README);
    control(0,L"BUTTON",L"Intento previo",BS_PUSHBUTTON|WS_TABSTOP,758,325,138,39,IDC_RESUME);
    control(0,L"STATIC",L"Resultado y registro",0,24,382,850,22,0);
    reportEdit=control(WS_EX_CLIENTEDGE,L"EDIT",L"Selecciona el CEX 3.2 y pulsa Convertir.\r\n\r\nSe conservan los originales. El archivo de salida debe abrirse y recalcularse en CE3X 2.3.\r\nNo se calculan consumos ni cumplimiento del CTE.",ES_MULTILINE|ES_READONLY|ES_AUTOVSCROLL|WS_VSCROLL|WS_TABSTOP,24,407,872,164,IDC_REPORT);
    control(0,L"STATIC",L"Si CE3X falla: indica la accion, el elemento y el mensaje exacto",0,24,587,850,22,0);
    notesEdit=control(WS_EX_CLIENTEDGE,L"EDIT",L"",ES_MULTILINE|ES_AUTOVSCROLL|WS_VSCROLL|WS_TABSTOP,24,613,577,78,IDC_NOTES);
    evidenceButton=control(0,L"BUTTON",L"Guardar error / adjunto",BS_PUSHBUTTON|WS_TABSTOP,620,613,276,39,IDC_EVIDENCE);
    control(0,L"STATIC",L"Puedes adjuntar un log o captura.\r\nCancelar guarda solo las notas.",0,620,657,276,42,0);
    control(0,L"STATIC",L"Sin instalacion y sin conexiones de red. Conserva toda esta carpeta junto al ejecutable.",0,24,712,870,24,0);
    EnableWindow(openButton,FALSE);EnableWindow(evidenceButton,FALSE);DragAcceptFiles(mainWindow,TRUE);
}
static LRESULT CALLBACK wndProc(HWND hwnd,UINT msg,WPARAM wp,LPARAM lp){
    switch(msg){
    case WM_CREATE:mainWindow=hwnd;initializeUI();return 0;
    case WM_COMMAND:
        if(running&&LOWORD(wp)!=IDC_OPEN)return 0;
        switch(LOWORD(wp)){
            case 201:browseFile(sourceEdit,FALSE);break;case 202:browseFile(templateEdit,FALSE);break;case 203:browseFolder();break;
            case IDC_CONVERT:convert();break;
            case IDC_RESUME:resumeRun();break;
            case IDC_OPEN:if(lastRun[0])ShellExecuteW(hwnd,L"open",lastRun,NULL,NULL,SW_SHOWNORMAL);break;
            case IDC_EVIDENCE:attachEvidence();break;
            case IDC_README:{WCHAR path[PATHCAP];swprintf(path,PATHCAP,L"%ls\\LEEME.txt",baseDir);ShellExecuteW(hwnd,L"open",path,NULL,NULL,SW_SHOWNORMAL);break;}
        }return 0;
    case WM_TIMER:{DWORD code;if(running&&GetExitCodeProcess(process.hProcess,&code)&&code!=STILL_ACTIVE){KillTimer(hwnd,1);finishProcess();}return 0;}
    case WM_DROPFILES:{HDROP drop=(HDROP)wp;WCHAR path[PATHCAP];if(!running&&DragQueryFileW(drop,0,path,PATHCAP))SetWindowTextW(sourceEdit,path);DragFinish(drop);return 0;}
    case WM_CLOSE:if(running){MessageBoxW(hwnd,L"Hay un proceso en marcha. Espera a que termine para conservar el diagnostico.",L"Conversor CE3X",MB_OK);return 0;}DestroyWindow(hwnd);return 0;
    case WM_DESTROY:if(font)DeleteObject(font);PostQuitMessage(0);return 0;
    }return DefWindowProcW(hwnd,msg,wp,lp);
}
int WINAPI wWinMain(HINSTANCE instance,HINSTANCE prev,PWSTR cmdline,int show){
    (void)prev;(void)cmdline;OleInitialize(NULL);
    GetModuleFileNameW(NULL,baseDir,PATHCAP);WCHAR *slash=wcsrchr(baseDir,L'\\');if(slash)*slash=0;
    WCHAR temp[MAX_PATH];GetTempPathW(MAX_PATH,temp);DWORD pid=GetCurrentProcessId();
    swprintf(bridgePath,PATHCAP,L"%lscex_conversor_%lu_resultado.txt",temp,(unsigned long)pid);
    swprintf(bootPath,PATHCAP,L"%lscex_conversor_%lu_arranque.log",temp,(unsigned long)pid);
    swprintf(notesPath,PATHCAP,L"%lscex_conversor_%lu_notas.txt",temp,(unsigned long)pid);
    int argc;WCHAR **argv=CommandLineToArgvW(GetCommandLineW(),&argc);
    // Modo de prueba del ejecutable y de su runtime, sin interaccion de usuario.
    if(argc>=3&&wcscmp(argv[1],L"--self-test")==0){
        wcsncpy(bridgePath,argv[2],PATHCAP-1);
        const WCHAR *args[]={L"self-test"};
        if(!startEngine(args,1,TRUE))return 2;
        WaitForSingleObject(process.hProcess,60000);DWORD code=1;GetExitCodeProcess(process.hProcess,&code);
        CloseHandle(process.hProcess);CloseHandle(process.hThread);LocalFree(argv);OleUninitialize();return (int)code;
    }
    WNDCLASSW wc={0};wc.lpfnWndProc=wndProc;wc.hInstance=instance;wc.lpszClassName=L"CE3XConversorWindow";wc.hCursor=LoadCursor(NULL,IDC_ARROW);wc.hbrBackground=(HBRUSH)(COLOR_BTNFACE+1);wc.hIcon=LoadIcon(NULL,IDI_APPLICATION);RegisterClassW(&wc);
    RECT rect={0,0,920,755};AdjustWindowRect(&rect,WS_OVERLAPPED|WS_CAPTION|WS_SYSMENU|WS_MINIMIZEBOX,FALSE);
    mainWindow=CreateWindowW(wc.lpszClassName,L"Conversor CE3X 3.2 a 2.3 - Diagnostico",WS_OVERLAPPED|WS_CAPTION|WS_SYSMENU|WS_MINIMIZEBOX,CW_USEDEFAULT,CW_USEDEFAULT,rect.right-rect.left,rect.bottom-rect.top,NULL,NULL,instance,NULL);
    if(!mainWindow)return 1;
    if(argc>=2)SetWindowTextW(sourceEdit,argv[1]);LocalFree(argv);
    ShowWindow(mainWindow,show);UpdateWindow(mainWindow);
    MSG msg;while(GetMessageW(&msg,NULL,0,0)>0){if(!IsDialogMessageW(mainWindow,&msg)){TranslateMessage(&msg);DispatchMessageW(&msg);}}
    OleUninitialize();return (int)msg.wParam;
}
