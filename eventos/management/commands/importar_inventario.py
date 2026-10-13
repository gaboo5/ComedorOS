from django.core.management.base import BaseCommand
from eventos.models import CategoriaInventario, ElementoInventario

# (nombre, categoria, cantidad) — transcripto de INVENTARIO_AGOSTO_2026.xlsx
# Se excluye "Copas De Degustación (no nos corresponde)" según lo acordado.
ITEMS = [
    # --- Cristalería ---
    ("Copas de Agua (300ml)", "Cristalería", 164),
    ("Copas de Vino (250ml)", "Cristalería", 533),
    ("Copas Emperatriz (480ml)", "Cristalería", 48),
    ("Copas de Champagne (210ml)", "Cristalería", 295),
    ("Copas Bouquet Agua", "Cristalería", 55),
    ("Chupitos Copas", "Cristalería", 69),
    ("Chupitos Frascos", "Cristalería", 404),
    ("Jarra (0,5Lts)", "Cristalería", 2),
    ("Jarra (1,5Lts)", "Cristalería", 22),
    ("Jarros de Vidrio (0,5Lts)", "Cristalería", 6),
    ("Vasos Trago Largo (Bermudas)", "Cristalería", 155),
    ("Vasos Facetados 375cc", "Cristalería", 205),
    ("Jarras Plásticas 1,5 Lts", "Cristalería", 2),

    # --- Vajilla ---
    ("Plato Cuadrado de Entrada", "Vajilla", 37),
    ("Plato Cuadrado de Postre", "Vajilla", 53),
    ("Plato Cuadrado de Principal", "Vajilla", 12),
    ("Plato Rectangular Chico", "Vajilla", 1),
    ("Plato Rectangular Grande", "Vajilla", 4),
    ("Plato Redondo Plallo (27cm) ACASU", "Vajilla", 181),
    ("Plato Triangular Negro Entrada", "Vajilla", 28),
    ("Plato Triangular Negro Postre", "Vajilla", 28),
    ("Plato Triangular Negro Principal", "Vajilla", 28),
    ("Platos Citio (Acero Inoxidable)", "Vajilla", 8),
    ("Platos para Pan", "Vajilla", 48),
    ("Platos Taza de Té", "Vajilla", 248),
    ("Platos Pentagonales", "Vajilla", 9),
    ("Pocillos de Café", "Vajilla", 32),
    ("Taza de Té y Café", "Vajilla", 149),

    # --- Bandejas ---
    ("Bandeja Acero Inoxidable Oval Hondo", "Bandejas", 2),
    ("Bandeja Acero Inoxidable Redonda Plalla", "Bandejas", 13),
    ("Bandeja Antideslizante Redonda Grande", "Bandejas", 2),
    ("Bandeja Antideslizante Redonda Mediana", "Bandejas", 5),
    ("Frapera Grande (1 en desuso)", "Bandejas", 8),
    ("Frapera Chica", "Bandejas", 13),
    ("Frapera de plástico", "Bandejas", 10),
    ("Pinzas para Hielo", "Bandejas", 4),
    ("Pinzas para Medialunas", "Bandejas", 1),

    # --- Cazuelas ---
    ("Cazuela Cuadrada con Base Inferior", "Cazuelas", 31),
    ("Cazuela Redonda Bambú Negras (9,5cm)", "Cazuelas", 6),
    ("Cazuela Redonda sin aza (9,5cm)", "Cazuelas", 57),
    ("Cazuela Redonda con aza (9,5cm)", "Cazuelas", 24),
    ("Cazuela Redonda (9-9,5-10cm)", "Cazuelas", 51),
    ("Cazuela Redonda (8cm)", "Cazuelas", 208),
    ("Cazuela Redonda de Cuatro Puntas", "Cazuelas", 19),
    ("Cazuela Oval de corte Diagonal", "Cazuelas", 6),
    ("Dips Medio Limón", "Cazuelas", 48),
    ("Dips Chico (Plástico)", "Cazuelas", 7),
    ("Bowl Redondo (simil plato hondo pero chico)", "Cazuelas", 48),
    ("Ensaladera Redonda", "Cazuelas", 8),
    ("Ensaladera Cuadrada", "Cazuelas", 11),
    ("Ensaladera Redonda Bambú Negras", "Cazuelas", 4),
    ("Ensaladera Redonda de Tres Puntas", "Cazuelas", 3),
    ("Fruteras (Bambú negras)", "Cazuelas", 6),
    ("Jarra Botella 0,5 Lts", "Cazuelas", 6),

    # --- Cubertería ---
    ("Cucharas Postre", "Cubertería", 81),
    ("Cucharas de Té/Café (Varios Modelos)", "Cubertería", 141),
    ("Huntadores", "Cubertería", 4),
    ("Cuchillos Metal", "Cubertería", 85),
    ("Tenedores Postre", "Cubertería", 24),
    ("Tenedores Metal", "Cubertería", 59),

    # --- Artículos Varios ---
    ("Alcuza (Nouvelle)", "Artículos Varios", 11),
    ("Alcuza Cerámica Blanca", "Artículos Varios", 0),
    ("Armario color Negro", "Artículos Varios", 1),
    ("Arrocera", "Artículos Varios", 5),
    ("Azucarera Cerámica", "Artículos Varios", 12),
    ("Banners", "Artículos Varios", 3),
    ("Braseros Enlozados color Negro", "Artículos Varios", 8),
    ("Cafetera Eléctrica 7Lts", "Artículos Varios", 1),
    ("Cajones Plástico Amarillo", "Artículos Varios", 5),
    ("Canasto Metálico", "Artículos Varios", 1),
    ("Chicotes Garrafa", "Artículos Varios", 1),
    ("Carlitera", "Artículos Varios", 1),
    ("Carro Metálico Cuatro Ruedas", "Artículos Varios", 2),
    ("Dispenser de Vidrio (3Lts)", "Artículos Varios", 1),
    ("Dispenser de Vidrio (5Lts)", "Artículos Varios", 2),
    ("Dispenser Plástico (Color Blanco)", "Artículos Varios", 2),
    ("Escurridores Plástico Amarillo", "Artículos Varios", 2),
    ("Estanterías Madera", "Artículos Varios", 2),
    ("Estanterías Metal", "Artículos Varios", 9),
    ("Estanterías Madera y Metal", "Artículos Varios", 1),
    ("Estantería Metal y Vidrio", "Artículos Varios", 1),
    ("Filtro Café nº 24", "Artículos Varios", 3),
    ("Filtro Café n° 16", "Artículos Varios", 1),
    ("Florero de Vidrio (40cm)", "Artículos Varios", 19),
    ("Florero de Vidrio Chico (Frascos)", "Artículos Varios", 8),
    ("Florero de vidrio Cuadrado", "Artículos Varios", 7),
    ("Freezer 60 Lts", "Artículos Varios", 1),
    ("Freidora", "Artículos Varios", 1),
    ("Fuente Cascada para Fondiu", "Artículos Varios", 1),
    ("Garrafa 10KG", "Artículos Varios", 1),
    ("Gazebo 3x6 (Color Blanco)", "Artículos Varios", 1),
    ("Guirnalda De Luces x10 Mts", "Artículos Varios", 1),
    ("Hielera Grande (60Lts)", "Artículos Varios", 2),
    ("Horno Grill", "Artículos Varios", 1),
    ("Licuadora de Vaso (ROTAS)", "Artículos Varios", 2),
    ("Madera Para Tortas", "Artículos Varios", 2),
    ("Mesa Rectangular", "Artículos Varios", 1),
    ("Microondas Philco 28lts", "Artículos Varios", 1),
    ("Moldes de Tarteletas (13x14cm y 7x10cm)", "Artículos Varios", 11),
    ("Olla Eléctrica", "Artículos Varios", 5),
    ("Olla Cocina nº20", "Artículos Varios", 1),
    ("Panchera", "Artículos Varios", 1),
    ("Parrilla para Tostados (par)", "Artículos Varios", 2),
    ("Pava eléctrica", "Artículos Varios", 1),
    ("Perchero", "Artículos Varios", 1),
    ("Pincel de Silicona", "Artículos Varios", 1),
    ("Prensa para Jamón", "Artículos Varios", 1),
    ("Rollo Papel Madera", "Artículos Varios", 1),
    ("Sillas", "Artículos Varios", 2),
    ("Tabla Para Picadas De Madera", "Artículos Varios", 4),
    ("Termo 12lts (3 en desuso) (8A-4R-1G)", "Artículos Varios", 13),
    ("Termo 1Lts (1N-1B)", "Artículos Varios", 2),
    ("Termo 0,75 Lts", "Artículos Varios", 2),
    ("Termo 2Lts (en Depósito) (1Bl)", "Artículos Varios", 1),
    ("Termo 5Lts (1N-1R-2V-1C)", "Artículos Varios", 5),
    ("Termo 9lts (1 en desuso C) (1A-3C-1R)", "Artículos Varios", 5),
    ("Termo acero Inoxidable 9Lts", "Artículos Varios", 1),
    ("Termo Eléctrico Cuadrado 6Lts", "Artículos Varios", 1),
    ("Tetera Cerámica", "Artículos Varios", 13),
    ("Paredes Gazebo 3x3", "Artículos Varios", 6),

    # --- Kit Coctelería ---
    ("Coctelera Bahía", "Kit Coctelería", 1),
    ("Cucharas para Hielo plástico Negro", "Kit Coctelería", 2),
    ("Difusor", "Kit Coctelería", 1),
    ("Jigger", "Kit Coctelería", 1),
    ("Pisones para tragos", "Kit Coctelería", 3),

    # --- Mantelería (incluye Servilleta, Cubre Silla, Cubre Manteles) ---
    ("Mantel Redondo Blanco", "Mantelería", 64),
    ("Mantel Redondo Negro", "Mantelería", 14),
    ("Mantel Rectangular Blanco", "Mantelería", 11),
    ("Mantel Rectangular Negro", "Mantelería", 3),
    ("Mantel Imperial Redondo Blanco", "Mantelería", 6),
    ("Mantel Imperial Rectangular Blanco", "Mantelería", 3),
    ("Servilleta Blanca", "Mantelería", 140),
    ("Cubre Sillas Blanco", "Mantelería", 256),
    ("Cubre Mantel Color Negro 1,40x1,40", "Mantelería", 9),
    ("Cubre Mantel Color Negro 2x2", "Mantelería", 1),
    ("Cubre Mantel Color Azul 1,40x1,40", "Mantelería", 14),
    ("Cubre Mantel Color Azul 2x2", "Mantelería", 5),
    ("Cubre Mantel Color Verde 1,40x1,40", "Mantelería", 4),
    ("Cubre Mantel Color Verde 2x2", "Mantelería", 10),
    ("Cubre Mantel Color Rosa 1,40x1,40", "Mantelería", 11),
    ("Cubre Mantel Color Salmón 1,40x1,40", "Mantelería", 3),
    ("Cubre Mantel Color Celeste 1,40x1,40", "Mantelería", 6),
    ("Cubre Mantel Color Crema 1,40x1,40", "Mantelería", 17),

    # --- Uniformes ---
    ("Camisas Blancas", "Uniformes", 8),
    ("Camisas Negras", "Uniformes", 6),
    ("Chombas Azules", "Uniformes", 6),
    ("Chalecos Negros", "Uniformes", 6),
    ("Corbatas Negras", "Uniformes", 10),
    ("Faldones Color Borra Vino", "Uniformes", 10),
]


class Command(BaseCommand):
    help = 'Importa el inventario desde INVENTARIO_AGOSTO_2026.xlsx (datos ya transcriptos y organizados).'

    def handle(self, *args, **options):
        creados = 0
        actualizados = 0
        for nombre, nombre_categoria, cantidad in ITEMS:
            categoria, _ = CategoriaInventario.objects.get_or_create(nombre=nombre_categoria)
            elemento, fue_creado = ElementoInventario.objects.update_or_create(
                nombre=nombre, categoria=categoria,
                defaults={'cantidad_total': cantidad}
            )
            if fue_creado:
                creados += 1
            else:
                actualizados += 1

        self.stdout.write(self.style.SUCCESS(
            f'Listo. {creados} elementos nuevos creados, {actualizados} actualizados '
            f'(de {len(ITEMS)} totales en {len(set(c for _, c, _ in ITEMS))} categorías).'
        ))
