import math
import os
import sys
import random
import pygame

# Garante que os caminhos relativos dos assets funcionem mesmo que o jogo
# seja executado a partir de outra pasta
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Inicialização do Pygame
pygame.init()
pygame.font.init()

# Configurações da Janela (Baseado na proporção 16:9 das imagens)
LARGURA, ALTURA = 1000, 562
# SCALED: o jogo continua "pensando" em 1000x562, mas a imagem é ampliada
# automaticamente na tela cheia (inclusive as coordenadas do mouse)
TELA = pygame.display.set_mode((LARGURA, ALTURA), pygame.SCALED)
pygame.display.set_caption("Run Cat Run!")

# FPS
CLOCK = pygame.time.Clock()
FPS = 60

# Pontuação: 1 ponto por segundo sobrevivido
META_PONTOS = 1000
VELOCIDADE_INICIAL = 6
VELOCIDADE_MAXIMA = 20
SEGUNDOS_POR_NIVEL = 50  # a cada 50 s a velocidade do jogo aumenta 1

# Linha da calçada onde ficam os "pés" do gato e dos obstáculos
CHAO_Y = 455
GATO_CENTRO_X = 150

# Justiça do jogo: tempo mínimo (em quadros) entre o pug passar pelo gato e um
# obstáculo de chão passar pelo gato. 45 quadros = 0,75 s, um pulo inteiro.
FOLGA_JUSTA = 45

# Cor de referência do fundo verde dos sprite sheets e a tolerância por canal
# (R, G, B). Como os arquivos são JPEG, o verde não é exatamente (0, 255, 0),
# então removemos todo pixel "parecido" com o verde do fundo.
VERDE_CHROMA = (50, 245, 5, 255)
TOLERANCIA_CHROMA = (65, 60, 75, 255)

PASTA = "assets/imagens/"
PASTA_SONS = "assets/imagens/sounds/"


# ==========================================
# CARREGAMENTO DE RECURSOS E ASSETS
# ==========================================
def carregar_imagem(nome):
  try:
    return pygame.image.load(PASTA + nome).convert()
  except (pygame.error, FileNotFoundError) as e:
    print(f"Erro ao carregar imagem {nome}: {e}")
    pygame.quit()
    sys.exit()


def carregar_tela(nome):
  """Carrega uma imagem e redimensiona para o tamanho da janela."""
  return pygame.transform.smoothscale(carregar_imagem(nome), (LARGURA, ALTURA))


def remover_fundo_verde(sheet):
  """Retorna uma cópia do sheet com o fundo verde transparente."""
  mascara = pygame.mask.from_threshold(sheet, VERDE_CHROMA, TOLERANCIA_CHROMA)
  mascara.invert()  # agora a máscara marca tudo que NÃO é verde
  return mascara.to_surface(
      setsurface=sheet.convert_alpha(), unsetcolor=(0, 0, 0, 0)
  ).convert_alpha()


def recortar_sprite(sheet, retangulo, escala, espelhar=False):
  """Recorta um sprite do sheet (x, y, largura, altura) e aplica a escala."""
  sprite = sheet.subsurface(pygame.Rect(retangulo)).copy()
  # Mantém só a maior figura do recorte (descarta pedaços de sprites vizinhos)
  figura = pygame.mask.from_surface(sprite).connected_component()
  sprite = figura.to_surface(setsurface=sprite, unsetcolor=(0, 0, 0, 0))
  largura = int(sprite.get_width() * escala)
  altura = int(sprite.get_height() * escala)
  sprite = pygame.transform.smoothscale(sprite, (largura, altura))
  if espelhar:
    sprite = pygame.transform.flip(sprite, True, False)
  return sprite


# Telas Estáticas
img_menu = carregar_tela("tela_menu.jpg")
img_controles = carregar_tela("tela_controles.jpg")
img_sobre = carregar_tela("tela_sobre.jpg")
img_gameover = carregar_tela("tela_gameover.jpg")
img_vitoria = carregar_tela("tela_vitoria.jpg")
img_cenario = carregar_tela("cenario_rua.jpeg")

# Sprite Sheets (já com o fundo verde removido)
gato_sheet = remover_fundo_verde(carregar_imagem("gato_sheet.jpeg"))
obstaculos_sheet = remover_fundo_verde(carregar_imagem("obstaculos_sheet.jpg"))
pug_sheet = remover_fundo_verde(carregar_imagem("pug_aviao_sheet.jpeg"))

# Posições (x, y, largura, altura) de cada pose dentro dos sheets originais
ESCALA_GATO = 0.33
FRAMES_CORRIDA = [
    recortar_sprite(gato_sheet, (18, 59, 318, 301), ESCALA_GATO),
    recortar_sprite(gato_sheet, (332, 75, 296, 284), ESCALA_GATO),
    recortar_sprite(gato_sheet, (636, 77, 253, 291), ESCALA_GATO),
    recortar_sprite(gato_sheet, (160, 439, 241, 269), ESCALA_GATO),
]
FRAME_PULO = recortar_sprite(gato_sheet, (893, 36, 260, 309), ESCALA_GATO)
FRAME_ABAIXADO = recortar_sprite(gato_sheet, (1060, 231, 296, 137), ESCALA_GATO)

ESCALA_OBSTACULO = 0.055
IMG_LIXEIRA = recortar_sprite(
    obstaculos_sheet, (275, 107, 884, 1309), ESCALA_OBSTACULO
)
IMG_HIDRANTE = recortar_sprite(
    obstaculos_sheet, (1770, 99, 676, 1340), ESCALA_OBSTACULO
)

# O pug voa da esquerda para a direita (mesma direção dos aviões no sheet)
ESCALA_PUG = 0.30
FRAMES_PUG = [
    recortar_sprite(pug_sheet, (109, 42, 473, 311), ESCALA_PUG),
    recortar_sprite(pug_sheet, (857, 415, 473, 310), ESCALA_PUG),
]
PUG_VELOCIDADE = 6  # pixels por quadro, além do bônus pela velocidade do jogo
CHANCE_PUG = 1 / 3  # chance de cada sorteio de obstáculo ser o pug

# Faixa horizontal ocupada pelo gato (usada no cálculo de justiça)
LARGURA_GATO = max(f.get_width() for f in FRAMES_CORRIDA + [FRAME_PULO])
GATO_X1 = GATO_CENTRO_X - LARGURA_GATO // 2
GATO_X2 = GATO_CENTRO_X + LARGURA_GATO // 2

FONTE_PLACAR = pygame.font.SysFont("Arial", 26, bold=True)
FONTE_AVISO = pygame.font.SysFont("Arial", 30, bold=True)
FONTE_DICA = pygame.font.SysFont("Arial", 15, bold=True)


# ==========================================
# SONS E MÚSICA
# ==========================================
def carregar_som(nome, volume=1.0):
  """Carrega um efeito sonoro. Se falhar (ex.: PC sem placa de som), o jogo
  continua funcionando, só que sem esse som."""
  try:
    som = pygame.mixer.Sound(PASTA_SONS + nome)
    som.set_volume(volume)
    return som
  except (pygame.error, FileNotFoundError) as e:
    print(f"Aviso: não foi possível carregar o som {nome}: {e}")
    return None


def tocar(som, repeticoes=0):
  if som:
    som.play(loops=repeticoes)


SOM_AVIAO = carregar_som("airplane_sound.mp3", 0.6)
SOM_GAMEOVER = carregar_som("gameover_sound.mp3")
SOM_PULO = carregar_som("jump_sound.mp3", 0.6)
SOM_MENU_SELECAO = carregar_som("menu_select_sound.mp3", 0.5)
SOM_MENU_CLIQUE = carregar_som("menu_click_sound.mp3")
SOM_VITORIA = carregar_som("victory_sound.mp3")

# Telas em que a música de fundo toca (não toca no Game Over nem na Vitória)
ESTADOS_COM_MUSICA = ["MENU", "CONTROLES", "SOBRE", "JOGANDO"]


def atualizar_musica(estado):
  """Liga a música de fundo nas telas certas e desliga nas outras. Como só
  liga quando ela não está tocando, a música continua sem reiniciar ao passar
  do menu para o jogo."""
  try:
    if estado in ESTADOS_COM_MUSICA:
      if not pygame.mixer.music.get_busy():
        pygame.mixer.music.load(PASTA_SONS + "background_sound.mp3")
        pygame.mixer.music.set_volume(0.5)
        pygame.mixer.music.play(loops=-1)  # -1 = repete para sempre
    else:
      pygame.mixer.music.stop()
  except pygame.error:
    pass  # sem áudio disponível: segue o jogo em silêncio


def parar_som_aviao():
  if SOM_AVIAO:
    SOM_AVIAO.fadeout(300)


# ==========================================
# BOTÕES DAS TELAS (áreas clicáveis desenhadas nas imagens)
# ==========================================
BOTAO_VOLTAR = [(pygame.Rect(270, 475, 460, 70), "MENU")]
BOTOES = {
    "MENU": [
        (pygame.Rect(30, 485, 320, 60), "CONTROLES"),
        (pygame.Rect(395, 485, 210, 60), "JOGANDO"),
        (pygame.Rect(730, 485, 195, 60), "SOBRE"),
    ],
    "CONTROLES": BOTAO_VOLTAR,
    "SOBRE": BOTAO_VOLTAR,
    "GAME_OVER": BOTAO_VOLTAR,
    "VITORIA": BOTAO_VOLTAR,
}


def botao_sob_mouse(estado, posicao):
  """Retorna o (retângulo, destino) do botão sob o mouse, ou None."""
  for botao in BOTOES.get(estado, []):
    if botao[0].collidepoint(posicao):
      return botao
  return None


# ==========================================
# CLASSE DO JOGADOR (GATO)
# ==========================================
class Gato(pygame.sprite.Sprite):

  def __init__(self):
    super().__init__()
    self.frames_correr = FRAMES_CORRIDA
    self.resetar()

  def resetar(self):
    self.frame_indice = 0
    self.vel_y = 0
    self.gravidade = 0.8
    self.pulando = False
    self.abaixado = False
    self.chao_y = CHAO_Y
    self.base_y = self.chao_y  # posição dos pés (parte de baixo do sprite)
    self.definir_imagem(self.frames_correr[0])

  def definir_imagem(self, imagem):
    # Os frames têm tamanhos diferentes: mantemos os pés sempre no mesmo lugar
    self.image = imagem
    self.rect = self.image.get_rect(
        midbottom=(GATO_CENTRO_X, int(self.base_y))
    )
    self.mask = pygame.mask.from_surface(self.image)

  def pular(self):
    if not self.pulando and not self.abaixado:
      self.vel_y = -16
      self.pulando = True
      tocar(SOM_PULO)

  def update(self):
    # Gravidade e Pulo
    self.vel_y += self.gravidade
    self.base_y += self.vel_y

    if self.base_y >= self.chao_y:
      self.base_y = self.chao_y
      self.pulando = False
      self.vel_y = 0

    # Escolha da imagem conforme o estado
    if self.pulando:
      self.definir_imagem(FRAME_PULO)
    elif self.abaixado:
      self.definir_imagem(FRAME_ABAIXADO)
    else:
      # Animação de corrida
      self.frame_indice += 0.15
      if self.frame_indice >= len(self.frames_correr):
        self.frame_indice = 0
      self.definir_imagem(self.frames_correr[int(self.frame_indice)])


# ==========================================
# CLASSE DE OBSTÁCULOS
# ==========================================
class Obstaculo(pygame.sprite.Sprite):

  def __init__(self, tipo, velocidade_jogo):
    super().__init__()
    self.tipo = tipo
    self.frames = None
    self.frame_indice = 0

    if tipo == "lixeira":
      self.image = IMG_LIXEIRA
      self.rect = self.image.get_rect(bottomleft=(LARGURA + 50, CHAO_Y))
    elif tipo == "hidrante":
      self.image = IMG_HIDRANTE
      self.rect = self.image.get_rect(bottomleft=(LARGURA + 50, CHAO_Y))
    elif tipo == "pug_aviao":
      # Obstáculo aéreo (Pug Aviador): vem por trás do gato, da esquerda para
      # a direita, na altura da cabeça. Desvia-se abaixando (seta para baixo).
      self.frames = FRAMES_PUG
      self.image = self.frames[0]
      self.velocidade = PUG_VELOCIDADE + velocidade_jogo // 4
      self.altura_voo = CHAO_Y - 58  # parte de baixo do avião
      self.tempo_voo = 0
      # Nasce fora da tela, à esquerda: o tempo até entrar serve de aviso
      self.rect = self.image.get_rect(
          bottomright=(-PUG_VELOCIDADE * FPS, self.altura_voo)
      )

    self.mask = pygame.mask.from_surface(self.image)

  def eh_aereo(self):
    return self.tipo == "pug_aviao"

  def janela_perigo(self, velocidade_jogo):
    """Intervalo (início, fim), em quadros a partir de agora, em que este
    obstáculo estará na mesma faixa horizontal que o gato."""
    if self.eh_aereo():
      # anda para a direita: entra pela esquerda do gato, sai pela direita
      inicio = (GATO_X1 - self.rect.right) / self.velocidade
      fim = (GATO_X2 - self.rect.left) / self.velocidade
    else:
      # anda para a esquerda: entra pela direita do gato, sai pela esquerda
      inicio = (self.rect.left - GATO_X2) / velocidade_jogo
      fim = (self.rect.right - GATO_X1) / velocidade_jogo
    return inicio, fim

  def update(self, velocidade_jogo):
    if self.eh_aereo():
      # Voa contra o sentido do cenário, ultrapassando o gato
      self.rect.x += self.velocidade

      # Leve balanço para cima e para baixo, para parecer que está voando
      self.tempo_voo += 1
      self.rect.bottom = self.altura_voo + int(5 * math.sin(self.tempo_voo / 8))

      # Animação da hélice do avião
      self.frame_indice = (self.frame_indice + 0.2) % len(self.frames)
      self.image = self.frames[int(self.frame_indice)]
      self.mask = pygame.mask.from_surface(self.image)

      if self.rect.left > LARGURA:
        self.kill()
    else:
      self.rect.x -= velocidade_jogo
      if self.rect.right < 0:
        self.kill()

  def chegando(self):
    """True enquanto o pug ainda não entrou na tela (para mostrar o aviso)."""
    return self.eh_aereo() and self.rect.right < 0


def obstaculo_e_justo(novo, obstaculos, velocidade_jogo):
  """Um obstáculo aéreo e um de chão nunca podem passar pelo gato ao mesmo
  tempo (não dá para pular e abaixar juntos). Exigimos uma folga de
  FOLGA_JUSTA quadros entre os dois."""
  ini_novo, fim_novo = novo.janela_perigo(velocidade_jogo)
  for outro in obstaculos:
    if outro.eh_aereo() == novo.eh_aereo():
      continue  # dois do mesmo tipo se resolvem com a mesma ação
    ini, fim = outro.janela_perigo(velocidade_jogo)
    if fim < 0:
      continue  # este já passou pelo gato
    if ini_novo < fim + FOLGA_JUSTA and ini < fim_novo + FOLGA_JUSTA:
      return False
  return True


def proximo_obstaculo(obstaculos, velocidade_jogo, pug_reservado):
  """Decide o próximo obstáculo. Retorna (novo_obstaculo_ou_None, pug_reservado).

  Regras:
  - Enquanto um pug estiver voando (ou chegando), não nasce nada no chão.
  - Quando o sorteio escolhe o pug, ele fica "reservado": o chão para de
    receber obstáculos até a pista liberar espaço para o pug entrar.
  """
  if any(o.eh_aereo() for o in obstaculos):
    return None, pug_reservado

  if pug_reservado or random.random() < CHANCE_PUG:
    pug = Obstaculo("pug_aviao", velocidade_jogo)
    if obstaculo_e_justo(pug, obstaculos, velocidade_jogo):
      return pug, False
    return None, True  # ainda há obstáculo no chão perto do gato: espera

  tipo = random.choice(["lixeira", "hidrante"])
  return Obstaculo(tipo, velocidade_jogo), False


def desenhar_aviso_pug(tela, obstaculos, quadro):
  """Desenha um "!" piscando na borda esquerda quando um pug está chegando."""
  for obstaculo in obstaculos:
    if obstaculo.chegando() and (quadro // 8) % 2 == 0:
      centro = (28, obstaculo.altura_voo - 40)
      pygame.draw.circle(tela, (230, 40, 30), centro, 20)
      pygame.draw.circle(tela, (255, 255, 255), centro, 20, 3)
      texto = FONTE_AVISO.render("!", True, (255, 255, 255))
      tela.blit(texto, texto.get_rect(center=centro))


# ==========================================
# LOOP PRINCIPAL DO JOGO
# ==========================================
def main():
  estado = "MENU"
  pontos = 0
  tempo_jogo_ms = 0  # tempo sobrevivido na partida atual, em milissegundos
  velocidade_jogo = VELOCIDADE_INICIAL
  quadro = 0  # contador de quadros, usado para efeitos que piscam
  botao_em_foco = None  # botão sob o mouse (para tocar o som só ao entrar)
  aviao_tocando = False
  pug_reservado = False  # o sorteio escolheu o pug e ele aguarda para entrar

  # Grupos
  gato = Gato()
  grupo_gato = pygame.sprite.GroupSingle(gato)
  grupo_obstaculos = pygame.sprite.Group()

  # Controle de spawn de obstáculos
  SPAWN_OBSTACULO = pygame.USEREVENT + 1
  pygame.time.set_timer(SPAWN_OBSTACULO, 1800)

  # Posição do fundo para o carrossel infinito
  bg_x = 0

  def mudar_estado(novo_estado):
    """Troca de tela e cuida dos sons ligados a essa troca."""
    nonlocal estado, botao_em_foco, aviao_tocando
    estado = novo_estado
    if estado == "GAME_OVER":
      tocar(SOM_GAMEOVER)  # toca uma única vez, ao perder
    elif estado == "VITORIA":
      tocar(SOM_VITORIA)
    if estado != "JOGANDO" and aviao_tocando:
      parar_som_aviao()
      aviao_tocando = False
    atualizar_musica(estado)
    # O botão que já estiver sob o mouse na tela nova não toca o som de foco
    botao_em_foco = botao_sob_mouse(estado, pygame.mouse.get_pos())

  atualizar_musica(estado)

  while True:
    # dt = milissegundos desde o quadro anterior. Limitamos a 100 ms para que
    # travadas (ex.: ao alternar tela cheia) não "pulem" vários segundos.
    dt = min(CLOCK.tick(FPS), 100)
    quadro += 1

    # --------------------------------------
    # 1. PROCESSAMENTO DE EVENTOS
    # --------------------------------------
    for evento in pygame.event.get():
      if evento.type == pygame.QUIT:
        pygame.quit()
        sys.exit()

      # Som ao passar o mouse sobre uma opção (só no momento em que entra nela)
      if evento.type == pygame.MOUSEMOTION:
        botao = botao_sob_mouse(estado, evento.pos)
        if botao and botao != botao_em_foco:
          tocar(SOM_MENU_SELECAO)
        botao_em_foco = botao

      if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
        botao = botao_sob_mouse(estado, evento.pos)
        if botao:
          tocar(SOM_MENU_CLIQUE)
          destino = botao[1]
          if destino == "JOGANDO":
            # Resetar jogo
            pontos = 0
            tempo_jogo_ms = 0
            velocidade_jogo = VELOCIDADE_INICIAL
            bg_x = 0
            gato.resetar()
            grupo_obstaculos.empty()
            pug_reservado = False
          mudar_estado(destino)

      if evento.type == pygame.KEYDOWN:
        # F11 (ou Alt+Enter) alterna entre janela e tela cheia em qualquer tela
        alt_enter = evento.key == pygame.K_RETURN and evento.mod & pygame.KMOD_ALT
        if evento.key == pygame.K_F11 or alt_enter:
          pygame.display.toggle_fullscreen()
          continue

        if estado == "JOGANDO":
          if evento.key in [pygame.K_SPACE, pygame.K_UP]:
            gato.pular()
          if evento.key in [pygame.K_DOWN, pygame.K_LCTRL]:
            gato.abaixado = True
        elif estado in ["GAME_OVER", "VITORIA", "CONTROLES", "SOBRE"]:
          if evento.key in [pygame.K_RETURN, pygame.K_ESCAPE]:
            tocar(SOM_MENU_CLIQUE)
            mudar_estado("MENU")

      if evento.type == pygame.KEYUP:
        if evento.key in [pygame.K_DOWN, pygame.K_LCTRL]:
          gato.abaixado = False

      if evento.type == SPAWN_OBSTACULO and estado == "JOGANDO":
        novo, pug_reservado = proximo_obstaculo(
            grupo_obstaculos, velocidade_jogo, pug_reservado
        )
        if novo:
          grupo_obstaculos.add(novo)
          # Intervalo aleatório até o próximo, para não ficar repetitivo
          pygame.time.set_timer(SPAWN_OBSTACULO, random.randint(1100, 2100))
        else:
          # Esperando o pug sair da tela (ou a pista liberar para ele entrar)
          pygame.time.set_timer(SPAWN_OBSTACULO, 250)

    # --------------------------------------
    # 2. ATUALIZAÇÃO DA LÓGICA (JOGANDO)
    # --------------------------------------
    if estado == "JOGANDO":
      # 1 ponto por segundo sobrevivido (tempo real, independe do FPS)
      tempo_jogo_ms += dt
      pontos = tempo_jogo_ms // 1000

      # Aumenta a dificuldade gradualmente com o tempo
      velocidade_jogo = min(
          VELOCIDADE_MAXIMA, VELOCIDADE_INICIAL + pontos // SEGUNDOS_POR_NIVEL
      )

      # Carrossel do Cenário
      bg_x -= velocidade_jogo
      if bg_x <= -LARGURA:
        bg_x = 0

      grupo_gato.update()
      grupo_obstaculos.update(velocidade_jogo)

      # Som do avião: toca enquanto algum pug estiver visível na tela
      aviao_na_tela = any(
          o.eh_aereo() and o.rect.colliderect(TELA.get_rect())
          for o in grupo_obstaculos
      )
      if aviao_na_tela and not aviao_tocando:
        tocar(SOM_AVIAO, repeticoes=-1)
        aviao_tocando = True
      elif not aviao_na_tela and aviao_tocando:
        parar_som_aviao()
        aviao_tocando = False

      # Colisão (Hit-kill) usando máscara: só conta se os pixels se tocarem,
      # ignorando a área transparente em volta dos sprites
      if pygame.sprite.spritecollideany(
          gato, grupo_obstaculos, pygame.sprite.collide_mask
      ):
        mudar_estado("GAME_OVER")

      # Condição de Vitória
      elif pontos >= META_PONTOS:
        mudar_estado("VITORIA")

    # --------------------------------------
    # 3. RENDERIZAÇÃO NA TELA
    # --------------------------------------
    TELA.fill((0, 0, 0))

    if estado == "MENU":
      TELA.blit(img_menu, (0, 0))
      dica = FONTE_DICA.render("F11: tela cheia", True, (255, 255, 255))
      TELA.blit(dica, dica.get_rect(topright=(LARGURA - 12, 8)))

    elif estado == "CONTROLES":
      TELA.blit(img_controles, (0, 0))

    elif estado == "SOBRE":
      TELA.blit(img_sobre, (0, 0))

    elif estado == "JOGANDO":
      # Desenha fundo em loop contínuo
      TELA.blit(img_cenario, (bg_x, 0))
      TELA.blit(img_cenario, (bg_x + LARGURA, 0))

      grupo_obstaculos.draw(TELA)
      grupo_gato.draw(TELA)
      desenhar_aviso_pug(TELA, grupo_obstaculos, quadro)

      # Placar na tela
      texto_pontos = FONTE_PLACAR.render(
          f"PONTOS: {pontos} / {META_PONTOS}", True, (255, 255, 255)
      )
      TELA.blit(texto_pontos, (30, 20))

    elif estado == "GAME_OVER":
      TELA.blit(img_gameover, (0, 0))

    elif estado == "VITORIA":
      TELA.blit(img_vitoria, (0, 0))

    pygame.display.flip()


if __name__ == "__main__":
  main()
