# -*- coding: utf-8 -*-
# Ejecutado SOLO con python27.dll oficial por el lanzador de pruebas de CI.
import sys
import os,json,traceback
sys.frozen="console_exe"
sys.executable=os.path.join(os.getcwd(),"cexv2.3.exe")
sys.path.insert(0,os.getcwd())
import __builtin__
__builtin__._=lambda s:s
class Field(object):
 def __init__(self,name=''):self.name=name
 def GetValue(self):return '1'
 def GetSelection(self):return 0
 def GetStringSelection(self):return 'Conocidas' if 'caracter' in self.name.lower() or 'propiedad' in self.name.lower() else 'Edificio Objeto'
 def __getattr__(self,n):return Field(n)
 def __call__(self,*a,**kw):return ''
 def __float__(self):return 1.0
 def __int__(self):return 1
 def __str__(self):return '1'
 def __unicode__(self):return u'1'
 def __getitem__(self,k):return Field(self.name)
class Dummy(object):
 def comprobarDatos(self):return ''
 def __getattr__(self,n):return Field(n)
names=['panelCubiertaConAire','panelCubiertaConTerreno','panelFachadaConAire','panelFachadaConEdificio','panelFachadaConTerreno','panelSueloConAire','panelSueloConTerreno','panelParticionVertical','panelParticionHorizontalSuperior','panelParticionHorizontalInferior']
results=[]
for name in names:
 try:
  module=__import__('Envolvente.'+name,fromlist=['Panel1'])
  obj=Dummy();obj.tipo='Cubierta' if 'Cubierta' in name else 'Fachada' if 'Fachada' in name else 'Suelo' if 'Suelo' in name else u'Partici\xf3n Interior'
  result=module.Panel1.cogerDatos.im_func(obj)
  results.append({'module':name,'length':len(result),'row':result})
 except Exception:
  results.append({'module':name,'error':traceback.format_exc()})
output=os.environ['CE3X_PROBE_OUTPUT']
with open(output,'wb') as f:f.write(json.dumps(results,encoding="latin1",ensure_ascii=True,indent=2,default=lambda o:unicode(o)).encode('ascii'))
print(json.dumps(results,encoding="latin1",ensure_ascii=True,indent=2,default=lambda o:unicode(o)))
