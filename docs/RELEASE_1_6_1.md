# CE3X 1.6.1

Corrige el error `E_NUMBER` que cancelaba la conversión cuando una mejora tenía
el volumen de acumulación vacío. El campo permanece vacío en 2.3, sin heredar
el volumen del edificio base.

Los campos numéricos comunes incompletos o incoherentes se transfieren con
aviso. Se mantienen las comprobaciones de estructura, serialización y entradas
para los cálculos de adaptación de elementos nuevos de 3.2.

Regresiones automáticas de los tres métodos de depósito, sus campos vacíos,
copias en mejoras y conservación de costes y original. La comprobación de estos
campos incompletos es estructural, no una validación de su recálculo en CE3X 2.3.

Descarga el ZIP de Windows y extrae todo antes de ejecutar. Revisa y completa
los datos pendientes en CE3X 2.3 antes de recalcular y emitir informes.
