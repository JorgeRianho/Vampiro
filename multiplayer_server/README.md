# Vampiro Multiplayer (Host + Moviles)

Esta carpeta añade un modo multijugador por red para tu juego:

- Un movil crea la partida (host).
- El resto entra con enlace o codigo de sala.
- Cada dispositivo reclama su jugador.
- Cada jugador envia sus pruebas.
- Se asignan objetivo + prueba en secreto.
- Cada jugador puede consultar su mision cuando quiera.
- Al confirmar una muerte, el asesino hereda el siguiente objetivo.
- Todos reciben avisos de muertes en tiempo real.

## Ejecutar en local

```bash
cd multiplayer_server
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

Abre `http://localhost:8000` solo para el host.

## Jugar solo con moviles (sin ordenador)

No necesitas APK obligatoriamente. La forma mas solida es desplegar el backend en la nube y usarlo como web app:

- Host y jugadores abren la URL publica desde el movil.
- Puedes instalarla en pantalla de inicio (PWA) para que se vea como app.
- No depende de que tu PC este encendido.

### Opcion recomendada: Render (facil)

Prerequisitos:
- Repositorio en GitHub con esta carpeta.
- Cuenta en Render.

Pasos:
1. Sube cambios a GitHub.
2. En Render: `New +` -> `Web Service` -> conecta tu repo.
3. Configuracion:
- `Root Directory`: `multiplayer_server`
- `Build Command`: `pip install -r requirements.txt`
- `Start Command`: `uvicorn app:app --host 0.0.0.0 --port $PORT`
4. Deploy.
5. Render te dara una URL `https://...onrender.com`.
6. Abre esa URL en movil y ya podeis jugar sin ordenador.

Tambien tienes blueprint listo en `/render.yaml` (en la raiz del repo `Vampiro`).

### Opcion alternativa: Railway

1. Crea servicio desde tu repo.
2. Selecciona carpeta `multiplayer_server`.
3. Railway detecta Python automaticamente.
4. Comando de inicio (si lo pide): `uvicorn app:app --host 0.0.0.0 --port $PORT`.
5. Publica y usa la URL `https://...up.railway.app`.

### Instalar como app en movil (sin APK)

- Android (Chrome): menu -> `Añadir a pantalla de inicio`.
- iPhone (Safari): compartir -> `Añadir a pantalla de inicio`.

Esto crea un icono de app y abre en modo standalone.

## Conectar varios moviles

`localhost` no funciona para otros dispositivos. Para compartir partida necesitas una URL accesible por los demas:

1. Misma WiFi (recomendado para pruebas)
- Saca la IP local del host (por ejemplo en Linux: `hostname -I`).
- Abre en el host: `http://TU_IP_LOCAL:8000` (ejemplo `http://192.168.1.34:8000`).
- En la app, en `URL compartida`, usa esa URL antes de `Crear partida`.
- Comparte el enlace que aparece.

2. Fuera de tu red (internet)
- Necesitas publicar el servidor con dominio/tunel/VPS (por ejemplo Cloudflare Tunnel, Tailscale Funnel, ngrok, etc.).
- Usa esa URL `https://...` en `URL compartida`.

## Modo tunel (cualquier sitio)

He dejado un script para levantar servidor + tunel de Cloudflare en un comando:

```bash
cd multiplayer_server
pip install -r requirements.txt
./scripts/run_public_tunnel.sh
```

El script te mostrara una URL `https://...trycloudflare.com`.

Usa esa URL asi:
- Abrela en el movil host.
- En el campo `URL compartida`, pega esa misma URL.
- Pulsa `Crear partida`.
- Comparte el enlace generado al resto.

Notas:
- El tunel de `trycloudflare.com` cambia cada vez que reinicias.
- Si cierras el script, la URL deja de funcionar.

## Flujo recomendado

1. Host: `Crear partida`.
2. Host: comparte enlace `/?room=XXXXXX` o codigo.
3. Host: define lista de jugadores.
4. Cada jugador: entra desde su movil y pulsa `Soy yo` en su nombre.
5. Host: define numero de pruebas por jugador y activa `Pedir pruebas`.
6. Cada jugador: envia sus pruebas.
7. Host: pulsa `Iniciar partida`.
8. Juego activo: cada jugador ve su objetivo y prueba, y usa `Confirmar asesinato` cuando complete la eliminacion.

## Notas

- La app valida que nadie reciba una prueba escrita por si mismo.
- Para empezar partida, todos los jugadores deben estar reclamados y haber enviado pruebas.
- Estado actual en memoria: si el servidor se reinicia, se pierden salas/partidas activas.
