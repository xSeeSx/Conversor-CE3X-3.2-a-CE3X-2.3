#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
int main(int argc,char **argv){
 if(argc!=3)return 2;SetCurrentDirectoryA(argv[1]);SetDllDirectoryA(argv[1]);
 HMODULE p=LoadLibraryA("python27.dll");if(!p){fprintf(stderr,"DLL error %lu\n",GetLastError());return 3;}
 void (*home)(char*)=(void*)GetProcAddress(p,"Py_SetPythonHome");void (*init)(void)=(void*)GetProcAddress(p,"Py_Initialize");int (*run)(const char*)=(void*)GetProcAddress(p,"PyRun_SimpleString");
 home(argv[1]);init();FILE *f=fopen(argv[2],"rb");if(!f)return 4;fseek(f,0,SEEK_END);long n=ftell(f);rewind(f);char *code=calloc(n+1,1);fread(code,1,n,f);fclose(f);int result=run(code);free(code);return result?5:0;
}
