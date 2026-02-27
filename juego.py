import random
from kivy.app import App
from kivy.core.window import Window
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.graphics import Color, Rectangle


COLOR_FONDO = (0.97, 0.95, 0.90, 1)
COLOR_TEXTO = (0.18, 0.14, 0.10, 1)
COLOR_PRINCIPAL = (0.89, 0.39, 0.22, 1)
COLOR_SECUNDARIO = (0.35, 0.54, 0.48, 1)
COLOR_INPUT_BG = (1, 1, 1, 1)
COLOR_INPUT_FG = (0.12, 0.12, 0.12, 1)

Window.clearcolor = COLOR_FONDO


class PantallaBase(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(*COLOR_FONDO)
            self._bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._actualizar_bg, size=self._actualizar_bg)

    def _actualizar_bg(self, *_):
        self._bg_rect.pos = self.pos
        self._bg_rect.size = self.size


def crear_boton(texto, font_size=22, size_hint=(1, 0.2), principal=True):
    color = COLOR_PRINCIPAL if principal else COLOR_SECUNDARIO
    return Button(
        text=texto,
        font_size=font_size,
        size_hint=size_hint,
        background_normal="",
        background_down="",
        background_color=color,
        color=(1, 1, 1, 1),
        bold=True,
    )


def crear_label(texto="", font_size=22, size_hint=(1, 0.2), negrita=False):
    return Label(
        text=texto,
        font_size=font_size,
        size_hint=size_hint,
        color=COLOR_TEXTO,
        bold=negrita,
    )


def crear_input(**kwargs):
    entrada = TextInput(**kwargs)
    entrada.background_normal = ""
    entrada.background_active = ""
    entrada.background_color = COLOR_INPUT_BG
    entrada.foreground_color = COLOR_INPUT_FG
    entrada.cursor_color = COLOR_PRINCIPAL
    return entrada


def normalizar_nombres_desde_inputs(inputs, etiqueta="Participante"):
    nombres = []
    usados = set()
    for i, entrada in enumerate(inputs, start=1):
        nombre = entrada.text.strip() or f"{etiqueta} {i}"
        base = nombre
        sufijo = 2
        while nombre.lower() in usados:
            nombre = f"{base} ({sufijo})"
            sufijo += 1
        usados.add(nombre.lower())
        nombres.append(nombre)
    return nombres


def generar_ciclo_unico(nombres):
    """
    Genera una asignacion de amigo invisible con un unico ciclo:
    A -> B -> C -> ... -> A
    """
    n = len(nombres)
    if n < 2:
        raise ValueError("Se necesitan al menos 2 participantes.")

    while True:
        perm = list(range(n))
        random.shuffle(perm)

        if any(i == perm[i] for i in range(n)):
            continue

        visitados = set()
        actual = 0
        for _ in range(n):
            visitados.add(actual)
            actual = perm[actual]

        if len(visitados) == n and actual == 0:
            asignaciones = {}
            for i, nombre in enumerate(nombres):
                asignaciones[nombre] = nombres[perm[i]]
            return asignaciones


def generar_reparto_vampiro(nombres, pruebas_por_jugador):
    if len(nombres) < 2:
        raise ValueError("Se necesitan al menos 2 jugadores.")

    jugadores = list(nombres)
    objetivos = generar_ciclo_unico(jugadores)

    pruebas_disponibles = []
    for jugador in jugadores:
        pruebas_jugador = [p.strip() for p in pruebas_por_jugador.get(jugador, []) if p.strip()]
        for idx, texto in enumerate(pruebas_jugador, start=1):
            pruebas_disponibles.append(
                {
                    "id": f"{jugador}-{idx}-{random.randint(1000, 9999)}",
                    "autor": jugador,
                    "texto": texto,
                }
            )

    if len(pruebas_disponibles) < len(jugadores):
        raise ValueError("No hay suficientes pruebas para repartir.")

    opciones = {}
    for jugador in jugadores:
        indices = [i for i, prueba in enumerate(pruebas_disponibles) if prueba["autor"] != jugador]
        random.shuffle(indices)
        if not indices:
            raise ValueError(f"No hay pruebas validas para {jugador}.")
        opciones[jugador] = indices

    orden_jugadores = list(jugadores)
    random.shuffle(orden_jugadores)
    asignada_a_prueba = {}

    def buscar(jugador, visitadas):
        for idx_prueba in opciones[jugador]:
            if idx_prueba in visitadas:
                continue
            visitadas.add(idx_prueba)
            if idx_prueba not in asignada_a_prueba or buscar(asignada_a_prueba[idx_prueba], visitadas):
                asignada_a_prueba[idx_prueba] = jugador
                return True
        return False

    for jugador in orden_jugadores:
        if not buscar(jugador, set()):
            raise ValueError("No se pudo generar un reparto valido de pruebas.")

    prueba_por_jugador = {}
    for idx_prueba, jugador in asignada_a_prueba.items():
        prueba_por_jugador[jugador] = pruebas_disponibles[idx_prueba]["texto"]

    reparto = {}
    for jugador in jugadores:
        reparto[jugador] = {
            "objetivo": objetivos[jugador],
            "prueba": prueba_por_jugador[jugador],
        }
    return reparto


def generar_pruebas_automaticas(nombres, pruebas_por_jugador=3):
    catalogo = [
        "hacer un brindis",
        "contar un chiste",
        "dar una palmada en el hombro",
        "pedir una foto en grupo",
        "intercambiar una servilleta",
        "hacer una pregunta personal",
        "pedir que te de su vaso un segundo",
        "hacer que te cuente su pelicula favorita",
        "hacer un choque de manos",
        "pedirle que te acompane a por agua",
        "hacer que te ensene una cancion",
        "cambiar de sitio por un minuto",
        "esconderle un objeto importante sin que se de cuenta",
        "hacerle que hable haciendo mimica",
        "Hacer que alguien te dé la razón tres veces seguidas",
        "Provocar que alguien cuente una anécdota suya",
        "Lograr que alguien repita una palabra después de ti.",
        "Conseguir que alguien te enseñe una foto del móvil.",
        "Lograr que alguien se quite una prenda",
    ]
    pruebas = {}
    for jugador in nombres:
        copia = list(catalogo)
        random.shuffle(copia)
        pruebas[jugador] = copia[:pruebas_por_jugador]
    return pruebas


class PantallaInicio(PantallaBase):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation="vertical", padding=40, spacing=24)
        layout.add_widget(crear_label("ELIGE MODO DE JUEGO", font_size=34, negrita=True))

        boton_vampiro = crear_boton("Vampiro", font_size=26, size_hint=(1, 0.3), principal=True)
        boton_vampiro.bind(on_press=self.ir_a_vampiro)
        layout.add_widget(boton_vampiro)

        boton_amigo = crear_boton("Amigo Invisible", font_size=26, size_hint=(1, 0.3), principal=False)
        boton_amigo.bind(on_press=self.ir_a_amigo)
        layout.add_widget(boton_amigo)

        self.add_widget(layout)

    def ir_a_vampiro(self, _):
        self.manager.current = "vampiro_config"

    def ir_a_amigo(self, _):
        self.manager.current = "amigo_config"


class PantallaVampiroConfig(PantallaBase):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.inputs_nombres = []

        self.layout = BoxLayout(orientation="vertical", padding=30, spacing=12)
        self.layout.add_widget(crear_label("Vampiro", font_size=34, size_hint=(1, 0.12), negrita=True))
        self.layout.add_widget(crear_label("Numero de jugadores", font_size=22, size_hint=(1, 0.1)))

        self.input_num = crear_input(
            text="4",
            multiline=False,
            input_filter="int",
            font_size=22,
            size_hint=(0.25, 0.12),
            halign="center",
        )
        self.layout.add_widget(self.input_num)

        boton_configurar = crear_boton("Configurar nombres", font_size=20, size_hint=(1, 0.12), principal=False)
        boton_configurar.bind(on_press=self.configurar_campos_nombres)
        self.layout.add_widget(boton_configurar)

        self.mensaje = crear_label("", font_size=18, size_hint=(1, 0.1))
        self.layout.add_widget(self.mensaje)

        self.scroll = ScrollView(size_hint=(1, 0.38))
        self.nombres_layout = GridLayout(cols=1, spacing=10, size_hint_y=None)
        self.nombres_layout.bind(minimum_height=self.nombres_layout.setter("height"))
        self.scroll.add_widget(self.nombres_layout)
        self.layout.add_widget(self.scroll)

        boton_continuar = crear_boton("Continuar", font_size=22, size_hint=(1, 0.13), principal=True)
        boton_continuar.bind(on_press=self.continuar)
        self.layout.add_widget(boton_continuar)

        boton_inicio = crear_boton("Volver al inicio", font_size=20, size_hint=(1, 0.11), principal=False)
        boton_inicio.bind(on_press=lambda _: setattr(self.manager, "current", "inicio"))
        self.layout.add_widget(boton_inicio)

        self.add_widget(self.layout)
        self.configurar_campos_nombres()

    def configurar_campos_nombres(self, _=None):
        texto_num = self.input_num.text.strip()
        if not texto_num:
            self.mensaje.text = "Indica cuantos jugadores hay."
            return
        num = int(texto_num)
        if num < 2:
            self.mensaje.text = "Minimo: 2 jugadores."
            return

        self.mensaje.text = f"Escribe los nombres de {num} jugadores."
        self.nombres_layout.clear_widgets()
        self.inputs_nombres = []
        for i in range(1, num + 1):
            entrada = crear_input(
                hint_text=f"Jugador {i}",
                multiline=False,
                font_size=20,
                size_hint_y=None,
                height=50,
            )
            self.inputs_nombres.append(entrada)
            self.nombres_layout.add_widget(entrada)

    def continuar(self, _):
        if not self.inputs_nombres:
            self.configurar_campos_nombres()
            if not self.inputs_nombres:
                return

        nombres = normalizar_nombres_desde_inputs(self.inputs_nombres, etiqueta="Jugador")
        app = App.get_running_app()
        app.vampiro_nombres = nombres
        self.manager.current = "vampiro_modo_pruebas"


class PantallaVampiroModoPruebas(PantallaBase):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation="vertical", padding=40, spacing=20)
        layout.add_widget(crear_label("Modo Vampiro", font_size=32, size_hint=(1, 0.2), negrita=True))
        layout.add_widget(crear_label("Como quieres gestionar las pruebas?", font_size=22, size_hint=(1, 0.2)))

        boton_manual = crear_boton("Elegir pruebas manualmente", font_size=22, size_hint=(1, 0.22), principal=True)
        boton_manual.bind(on_press=lambda _: setattr(self.manager, "current", "vampiro_num_pruebas"))
        layout.add_widget(boton_manual)

        boton_auto = crear_boton("Recibir pruebas automaticas", font_size=22, size_hint=(1, 0.22), principal=False)
        boton_auto.bind(on_press=self.usar_pruebas_automaticas)
        layout.add_widget(boton_auto)

        self.mensaje = crear_label("", font_size=18, size_hint=(1, 0.1))
        layout.add_widget(self.mensaje)

        boton_atras = crear_boton("Volver", font_size=20, size_hint=(1, 0.16), principal=False)
        boton_atras.bind(on_press=lambda _: setattr(self.manager, "current", "vampiro_config"))
        layout.add_widget(boton_atras)

        self.add_widget(layout)

    def usar_pruebas_automaticas(self, _):
        app = App.get_running_app()
        try:
            pruebas = generar_pruebas_automaticas(app.vampiro_nombres, pruebas_por_jugador=3)
            reparto = generar_reparto_vampiro(app.vampiro_nombres, pruebas)
        except ValueError as exc:
            self.mensaje.text = str(exc)
            return

        pantalla = self.manager.get_screen("vampiro_reparto")
        pantalla.iniciar_reparto(reparto)
        self.manager.current = "vampiro_reparto"


class PantallaVampiroNumPruebas(PantallaBase):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation="vertical", padding=40, spacing=20)
        layout.add_widget(crear_label("Pruebas por jugador", font_size=30, size_hint=(1, 0.2), negrita=True))
        layout.add_widget(crear_label("Cuantas pruebas pondra cada jugador?", font_size=22, size_hint=(1, 0.2)))

        self.input_num = crear_input(
            text="3",
            multiline=False,
            input_filter="int",
            font_size=24,
            size_hint=(0.3, 0.2),
            halign="center",
        )
        layout.add_widget(self.input_num)

        self.mensaje = crear_label("", font_size=18, size_hint=(1, 0.14))
        layout.add_widget(self.mensaje)

        boton = crear_boton("Continuar", font_size=22, size_hint=(1, 0.2), principal=True)
        boton.bind(on_press=self.continuar)
        layout.add_widget(boton)

        boton_atras = crear_boton("Volver", font_size=20, size_hint=(1, 0.16), principal=False)
        boton_atras.bind(on_press=lambda _: setattr(self.manager, "current", "vampiro_modo_pruebas"))
        layout.add_widget(boton_atras)
        self.add_widget(layout)

    def continuar(self, _):
        texto = self.input_num.text.strip()
        if not texto:
            self.mensaje.text = "Indica un numero de pruebas."
            return
        num = int(texto)
        if num < 1:
            self.mensaje.text = "Debe ser al menos 1."
            return

        app = App.get_running_app()
        app.vampiro_pruebas_por_jugador = num
        pantalla = self.manager.get_screen("vampiro_carga_pruebas")
        pantalla.iniciar_carga(app.vampiro_nombres, num)
        self.manager.current = "vampiro_carga_pruebas"


class PantallaVampiroCargaPruebas(PantallaBase):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.nombres = []
        self.pruebas_por_jugador = 0
        self.indice = 0
        self.pruebas_guardadas = {}
        self.inputs_pruebas = []

        self.layout = BoxLayout(orientation="vertical", padding=30, spacing=12)
        self.titulo = crear_label("Carga secreta de pruebas", font_size=30, size_hint=(1, 0.13), negrita=True)
        self.layout.add_widget(self.titulo)

        self.subtitulo = crear_label("", font_size=20, size_hint=(1, 0.12))
        self.layout.add_widget(self.subtitulo)

        self.mensaje = crear_label("", font_size=17, size_hint=(1, 0.1))
        self.layout.add_widget(self.mensaje)

        self.scroll = ScrollView(size_hint=(1, 0.45))
        self.pruebas_layout = GridLayout(cols=1, spacing=10, size_hint_y=None)
        self.pruebas_layout.bind(minimum_height=self.pruebas_layout.setter("height"))
        self.scroll.add_widget(self.pruebas_layout)
        self.layout.add_widget(self.scroll)

        self.boton = crear_boton("Guardar y siguiente", font_size=22, size_hint=(1, 0.2), principal=True)
        self.boton.bind(on_press=self.guardar_y_siguiente)
        self.layout.add_widget(self.boton)

        self.add_widget(self.layout)

    def iniciar_carga(self, nombres, pruebas_por_jugador):
        self.nombres = list(nombres)
        self.pruebas_por_jugador = pruebas_por_jugador
        self.indice = 0
        self.pruebas_guardadas = {}
        self._preparar_turno()

    def _preparar_turno(self):
        if self.indice >= len(self.nombres):
            app = App.get_running_app()
            app.vampiro_pruebas = dict(self.pruebas_guardadas)
            try:
                reparto = generar_reparto_vampiro(self.nombres, self.pruebas_guardadas)
            except ValueError as exc:
                self.mensaje.text = str(exc)
                return
            pantalla = self.manager.get_screen("vampiro_reparto")
            pantalla.iniciar_reparto(reparto)
            self.manager.current = "vampiro_reparto"
            return

        jugador = self.nombres[self.indice]
        self.subtitulo.text = (
            f"Pasa el movil a: {jugador}\n"
            f"Escribe {self.pruebas_por_jugador} pruebas."
        )
        self.mensaje.text = ""
        self.pruebas_layout.clear_widgets()
        self.inputs_pruebas = []

        for i in range(1, self.pruebas_por_jugador + 1):
            entrada = crear_input(
                hint_text=f"Prueba {i}",
                multiline=False,
                font_size=20,
                size_hint_y=None,
                height=52,
            )
            self.inputs_pruebas.append(entrada)
            self.pruebas_layout.add_widget(entrada)

    def guardar_y_siguiente(self, _):
        jugador = self.nombres[self.indice]
        pruebas = []
        for i, entrada in enumerate(self.inputs_pruebas, start=1):
            texto = entrada.text.strip()
            pruebas.append(texto if texto else f"Prueba {i} de {jugador}")
        self.pruebas_guardadas[jugador] = pruebas
        self.indice += 1
        self._preparar_turno()


class PantallaVampiroReparto(PantallaBase):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.reparto = {}
        self.orden = []
        self.indice = 0
        self.mostrando = False

        layout = BoxLayout(orientation="vertical", padding=40, spacing=20)
        layout.add_widget(crear_label("Reparto Vampiro", font_size=32, size_hint=(1, 0.2), negrita=True))
        self.texto = crear_label("", font_size=24, size_hint=(1, 0.5))
        layout.add_widget(self.texto)
        self.boton = crear_boton("Continuar", font_size=24, size_hint=(1, 0.2), principal=True)
        self.boton.bind(on_press=self.siguiente)
        layout.add_widget(self.boton)
        self.add_widget(layout)

    def iniciar_reparto(self, reparto):
        self.reparto = dict(reparto)
        self.orden = list(self.reparto.keys())
        random.shuffle(self.orden)
        self.indice = 0
        self.mostrando = False
        self._actualizar()

    def _actualizar(self):
        if self.indice >= len(self.orden):
            self.manager.current = "vampiro_fin"
            return

        jugador = self.orden[self.indice]
        if not self.mostrando:
            self.texto.text = f"Pasa el movil a: {jugador}\n\nPulsa para revelar."
            self.boton.text = "Revelar"
        else:
            datos = self.reparto[jugador]
            self.texto.text = (
                f"{jugador}, tu objetivo es:\n{datos['objetivo']}\n\n"
                f"Forma de asesinato:\n{datos['prueba']}"
            )
            self.boton.text = "Ocultar y pasar"

    def siguiente(self, _):
        if not self.mostrando:
            self.mostrando = True
        else:
            self.mostrando = False
            self.indice += 1
        self._actualizar()


class PantallaVampiroFin(PantallaBase):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation="vertical", padding=40, spacing=20)
        layout.add_widget(crear_label("Modo Vampiro listo", font_size=34, negrita=True))
        layout.add_widget(crear_label("Todos tienen objetivo y prueba.", font_size=24))
        boton = crear_boton("Volver al inicio", font_size=22, size_hint=(1, 0.25), principal=False)
        boton.bind(on_press=lambda _: setattr(self.manager, "current", "inicio"))
        layout.add_widget(boton)
        self.add_widget(layout)


class PantallaAmigoConfig(PantallaBase):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.inputs_nombres = []

        self.layout = BoxLayout(orientation="vertical", padding=30, spacing=12)
        self.layout.add_widget(crear_label("Amigo Invisible", font_size=34, size_hint=(1, 0.12), negrita=True))
        self.layout.add_widget(crear_label("Numero de participantes", font_size=22, size_hint=(1, 0.1)))

        self.input_num = crear_input(
            text="4",
            multiline=False,
            input_filter="int",
            font_size=22,
            size_hint=(0.25, 0.12),
            halign="center",
        )
        self.layout.add_widget(self.input_num)

        boton_configurar = crear_boton("Configurar nombres", font_size=20, size_hint=(1, 0.12), principal=False)
        boton_configurar.bind(on_press=self.configurar_campos_nombres)
        self.layout.add_widget(boton_configurar)

        self.mensaje = crear_label("", font_size=18, size_hint=(1, 0.1))
        self.layout.add_widget(self.mensaje)

        self.scroll = ScrollView(size_hint=(1, 0.38))
        self.nombres_layout = GridLayout(cols=1, spacing=10, size_hint_y=None)
        self.nombres_layout.bind(minimum_height=self.nombres_layout.setter("height"))
        self.scroll.add_widget(self.nombres_layout)
        self.layout.add_widget(self.scroll)

        boton_empezar = crear_boton("Sortear y empezar reparto secreto", font_size=22, size_hint=(1, 0.13), principal=True)
        boton_empezar.bind(on_press=self.empezar_reparto)
        self.layout.add_widget(boton_empezar)

        boton_inicio = crear_boton("Volver al inicio", font_size=20, size_hint=(1, 0.11), principal=False)
        boton_inicio.bind(on_press=lambda _: setattr(self.manager, "current", "inicio"))
        self.layout.add_widget(boton_inicio)

        self.add_widget(self.layout)
        self.configurar_campos_nombres()

    def configurar_campos_nombres(self, _=None):
        texto_num = self.input_num.text.strip()
        if not texto_num:
            self.mensaje.text = "Indica cuantas personas juegan."
            return

        num = int(texto_num)
        if num < 2:
            self.mensaje.text = "Minimo: 2 participantes."
            return

        self.mensaje.text = f"Escribe los nombres de {num} participantes."
        self.nombres_layout.clear_widgets()
        self.inputs_nombres = []

        for i in range(1, num + 1):
            entrada = crear_input(
                hint_text=f"Participante {i}",
                multiline=False,
                font_size=20,
                size_hint_y=None,
                height=50,
            )
            self.inputs_nombres.append(entrada)
            self.nombres_layout.add_widget(entrada)

    def empezar_reparto(self, _):
        if not self.inputs_nombres:
            self.configurar_campos_nombres()
            if not self.inputs_nombres:
                return

        nombres = normalizar_nombres_desde_inputs(self.inputs_nombres, etiqueta="Participante")

        try:
            asignaciones = generar_ciclo_unico(nombres)
        except ValueError as exc:
            self.mensaje.text = str(exc)
            return

        pantalla_reparto = self.manager.get_screen("amigo_reparto")
        pantalla_reparto.iniciar_reparto(nombres, asignaciones)
        self.manager.current = "amigo_reparto"


class PantallaAmigoReparto(PantallaBase):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.nombres = []
        self.asignaciones = {}
        self.orden_reparto = []
        self.indice = 0
        self.mostrando_objetivo = False

        layout = BoxLayout(orientation="vertical", padding=40, spacing=20)
        self.label_titulo = crear_label("Reparto secreto", font_size=32, size_hint=(1, 0.2), negrita=True)
        layout.add_widget(self.label_titulo)

        self.label_texto = crear_label("", font_size=24, size_hint=(1, 0.5))
        layout.add_widget(self.label_texto)

        self.boton = crear_boton("Continuar", font_size=24, size_hint=(1, 0.2), principal=True)
        self.boton.bind(on_press=self.siguiente_paso)
        layout.add_widget(self.boton)

        self.add_widget(layout)

    def iniciar_reparto(self, nombres, asignaciones):
        self.nombres = list(nombres)
        self.asignaciones = dict(asignaciones)
        self.orden_reparto = list(nombres)
        random.shuffle(self.orden_reparto)
        self.indice = 0
        self.mostrando_objetivo = False
        self.actualizar_texto()

    def actualizar_texto(self):
        if self.indice >= len(self.orden_reparto):
            self.manager.current = "fin"
            return

        jugador = self.orden_reparto[self.indice]
        if not self.mostrando_objetivo:
            self.label_texto.text = (
                f"Pasa el movil a: {jugador}\n\n"
                "Pulsa para revelar su amigo invisible."
            )
            self.boton.text = "Revelar"
        else:
            objetivo = self.asignaciones[jugador]
            self.label_texto.text = (
                f"{jugador}, tu amigo invisible es:\n\n"
                f"{objetivo}"
            )
            self.boton.text = "Ocultar y pasar"

    def siguiente_paso(self, _):
        if self.indice >= len(self.orden_reparto):
            self.manager.current = "fin"
            return

        if not self.mostrando_objetivo:
            self.mostrando_objetivo = True
        else:
            self.mostrando_objetivo = False
            self.indice += 1

        self.actualizar_texto()


class PantallaFin(PantallaBase):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation="vertical", padding=40, spacing=20)
        layout.add_widget(crear_label("Reparto terminado", font_size=34, negrita=True))
        layout.add_widget(crear_label("Ya podeis empezar el juego.", font_size=24))

        boton_inicio = crear_boton("Volver al inicio", font_size=22, size_hint=(1, 0.25), principal=False)
        boton_inicio.bind(on_press=lambda _: setattr(self.manager, "current", "inicio"))
        layout.add_widget(boton_inicio)
        self.add_widget(layout)


class VampiroApp(App):
    def build(self):
        self.vampiro_nombres = []
        self.vampiro_pruebas_por_jugador = 0
        self.vampiro_pruebas = {}

        sm = ScreenManager()
        sm.add_widget(PantallaInicio(name="inicio"))
        sm.add_widget(PantallaVampiroConfig(name="vampiro_config"))
        sm.add_widget(PantallaVampiroModoPruebas(name="vampiro_modo_pruebas"))
        sm.add_widget(PantallaVampiroNumPruebas(name="vampiro_num_pruebas"))
        sm.add_widget(PantallaVampiroCargaPruebas(name="vampiro_carga_pruebas"))
        sm.add_widget(PantallaVampiroReparto(name="vampiro_reparto"))
        sm.add_widget(PantallaVampiroFin(name="vampiro_fin"))
        sm.add_widget(PantallaAmigoConfig(name="amigo_config"))
        sm.add_widget(PantallaAmigoReparto(name="amigo_reparto"))
        sm.add_widget(PantallaFin(name="fin"))
        return sm


if __name__ == "__main__":
    VampiroApp().run()
