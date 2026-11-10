[Sistema Boardsinc]([img/sistema BoardSinc.png](https://github.com/Khania93/BoardSinc/upload/main/img#:~:text=Sistema_BoardSinc.png))

## Actors del sistema
#### 3.1. Jugador tradicional o casual
És l'usuari que utilitza la plataforma com a eina de consulta i suport
durant les partides. Les seves funcions principals són:
- Consultar regles, manuals, cartes i fitxes digitals.
- Configurar llistes d'exèrcits i unitats abans de jugar.
- Registrar els resultats de les partides.
#### 3.2. Jugador competitiu o registrat
És el jugador que, a més de les funcions habituals, vol fer un seguiment
de la seva activitat i participar en el rànquing. Pot:
- Utilitzar miniatures equipades amb xips NFC per identificar les
  unitats i agilitzar-ne el desplegament.
- Consultar el seu perfil i l'historial de partides.
- Revisar les seves estadístiques i la seva posició al rànquing.
#### 3.3. Administrador i creador de contingut
És el responsable de mantenir la informació disponible a la plataforma i
supervisar-ne l'ús. Pot:
- Gestionar la base de dades dels jocs.
- Actualitzar manuals, cartes, errates i regles.
- Moderar el rànquing i els usuaris.
- Gestionar possibles incidències del sistema.
#### 3.4. Lector NFC
És el dispositiu que permet llegir les etiquetes NFC incorporades a les
miniatures físiques. Pot ser un telèfon intel·ligent o una tauleta amb
NFC, o bé un lector extern connectat al dispositiu de l'usuari.

El lector no és un usuari humà, sinó un element perifèric que facilita
la comunicació entre les miniatures físiques i la plataforma digital.
## 4. Abast del projecte
#### 4.1. Inclòs en el projecte
D'acord amb les funcionalitats descrites, l'abast previst del sistema
inclou:
- Una aplicació web i/o mòbil per accedir a les funcionalitats de la
  plataforma.
- La consulta de manuals, regles, cartes i fitxes digitals.
- La configuració de llistes d'exèrcits i unitats.
- La gestió de perfils d'usuari i l'autenticació.
- El registre de partides i dels seus resultats.
- La consulta de l'historial, les estadístiques i el rànquing dels
  jugadors registrats.
- La gestió administrativa dels continguts i dels usuaris.
- L'associació d'identificadors NFC amb miniatures o unitats.
- La lectura d'etiquetes NFC mitjançant dispositius compatibles.
- La sincronització dels canvis d'estat de les partides entre els
  dispositius participants.
#### 4.2. Elements físics i dependències
El funcionament de la identificació NFC requereix etiquetes o xips NFC
incorporats a les bases de les miniatures i un dispositiu capaç de
llegir-los.

Com a opcions de maquinari es contemplen etiquetes dels tipus
NTAG213 o NTAG215, així com telèfons i tauletes amb NFC integrat
o lectors externs USB/Bluetooth.

La disponibilitat i compatibilitat d'aquests dispositius són
dependències del sistema. No es concreta si el projecte fabricarà o
distribuirà aquests elements físics.
####4.3. Fora de l'abast o pendent de concretar
La documentació disponible no especifica si el projecte inclourà:
- El disseny, la fabricació o la distribució de miniatures i etiquetes
  NFC.
- La compra o fabricació de lectors NFC dedicats.
