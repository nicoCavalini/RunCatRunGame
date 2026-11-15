import sys
import random
import pygame

# Inicialização do Pygame
pygame.init()
pygame.font.init()

# Configurações da Janela (Baseado na proporção 16:9 das imagens)
LARGURA, ALTURA = 1000, 562
TELA = pygame.display.set_mode((LARGURA, ALTURA))
pygame.display.set_caption("Run Cat Run!")

# FPS
CLOCK = pygame.time.Clock()
FPS = 60

# Cores auxiliares
VERDE_CHROMA = (0, 255, 0)


# ==========================================
# CARREGAMENTO DE RECURSOS E ASSETS
# ==========================================
def carregar_imagem(caminho, converter_alfa=False):
  try:
    img = pygame.image.load(caminho)
    return img.convert_alpha() if converter_alfa else img.convert()
  except pygame.error as e:
    print(f"Erro ao carregar imagem {caminho}: {e}")
    pygame.quit()
    sys.exit()


# Telas Estáticas
img_menu = carregar_imagem("assets/imagens/tela_menu.jpg")
img_controles = carregar_imagem("assets/imagens/tela_controles.jpg")
img_sobre = carregar_imagem("assets/imagens/tela_sobre.jpg")
img_gameover = carregar_imagem("assets/imagens/tela_gameover.jpg")
img_vitoria = carregar_imagem("assets/imagens/tela_vitoria.jpg")
img_cenario = carregar_imagem("assets/imagens/cenario_rua.jpg")

# Redimensionar imagens estáticas para o tamanho da tela (caso necessário)
img_menu = pygame.transform.scale(img_menu, (LARGURA, ALTURA))
img_controles = pygame.transform.scale(img_controles, (LARGURA, ALTURA))
img_sobre = pygame.transform.scale(img_sobre, (LARGURA, ALTURA))
img_gameover = pygame.transform.scale(img_gameover, (LARGURA, ALTURA))
img_vitoria = pygame.transform.scale(img_vitoria, (LARGURA, ALTURA))
img_cenario = pygame.transform.scale(img_cenario, (LARGURA, ALTURA))

# Carregamento de Sprite Sheets
gato_sheet = carregar_imagem("assets/imagens/gato_sheet.jpg")
obstaculos_sheet = carregar_imagem("assets/imagens/obstaculos_sheet.jpg")
pug_sheet = carregar_imagem("assets/imagens/pug_aviao_sheet.jpg")


# Função auxiliar para recortar sprites da sheet e aplicar colorkey
def recortar_sprite(sheet, x, y, largura, altura, escala=(80, 80)):
  sprite = pygame.Surface((largura, altura))
  sprite.blit(sheet, (0, 0), (x, y, largura, altura))
  sprite.set_colorkey(VERDE_CHROMA)
  return pygame.transform.scale(sprite, escala)


# ==========================================
# CLASSE DO JOGADOR (GATO)
# ==========================================
class Gato(pygame.sprite.Sprite):

  def __init__(self):
    super().__init__()
    # Nota: Ajuste as coordenadas x, y, largura, altura conforme o recorte exato da sua sheet de gato
    # Aqui criamos uma estrutura base para extração dos frames da sheet horizontal
    self.frames_correr = []
    # Exemplo simulando 3 frames de corrida na sheet (divida o eixo X conforme necessário)
    largura_f, altura_f = 120, 120
    for i in range(3):
      frame = recortar_sprite(
          gato_sheet, i * largura_f, 0, largura_f, altura_f, (85, 85)
      )
      self.frames_correr.append(frame)

    self.frame_indice = 0
    self.image = self.frames_correr[self.frame_indice]
    self.rect = self.image.get_rect()
    self.rect.x = 100
    self.rect.y = 390  # Altura na calçada

    self.vel_y = 0
    self.gravidade = 0.8
    self.pulando = False
    self.abaixado = False
    self.chao_y = 390

  def pular(self):
    if not self.pulando and not self.abaixado:
      self.vel_y = -15
      self.pulando = True

  def atualizar(self):
    # Gravidade e Pulo
    self.vel_y += self.gravidade
    self.rect.y += self.vel_y

    if self.rect.y >= self.chao_y:
      self.rect.y = self.chao_y
      self.pulando = False
      self.vel_y = 0

    # Animação de corrida
    if not self.pulando and not self.abaixado:
      self.frame_indice += 0.15
      if self.frame_indice >= len(self.frames_correr):
        self.frame_indice = 0
      self.image = self.frames_correr[int(self.frame_indice)]


# ==========================================
# CLASSE DE OBSTÁCULOS
# ==========================================
class Obstaculo(pygame.sprite.Sprite):

  def __init__(self, tipo):
    super().__init__()
    self.tipo = tipo
    if tipo == "lixeira":
      # Recorta lixeira da obstaculos_sheet
      self.image = recortar_sprite(
          obstaculos_sheet, 0, 0, 200, 200, (65, 75)
      )
      self.rect = self.image.get_rect()
      self.rect.x = LARGURA + 50
      self.rect.y = 405
    elif tipo == "hidrante":
      # Recorta hidrante da obstaculos_sheet
      self.image = recortar_sprite(
          obstaculos_sheet, 200, 0, 200, 200, (55, 65)
      )
      self.rect = self.image.get_rect()
      self.rect.x = LARGURA + 50
      self.rect.y = 415
    elif tipo == "pug_aviao":
      # Obstáculo aéreo (Pug Aviador)
      self.image = recortar_sprite(pug_sheet, 0, 0, 250, 150, (90, 60))
      self.rect = self.image.get_rect()
      self.rect.x = LARGURA + 50
      self.rect.y = 300  # Voa mais alto

  def update(self, velocidade_jogo):
    self.rect.x -= velocidade_jogo
    if self.rect.x < -100:
      self.kill()


# ==========================================
# LOOP PRINCIPAL DO JOGO
# ==========================================
def main():
  estado = "MENU"
  pontos = 0
  velocidade_jogo = 6

  # Grupos
  gato = Gato()
  grupo_gato = pygame.sprite.GroupSingle(gato)
  grupo_obstaculos = pygame.sprite.Group()

  # Controle de spawn de obstáculos
  SPAWN_OBSTACULO = pygame.USEREVENT + 1
  pygame.time.set_timer(SPAWN_OBSTACULO, 1800)

  # Posição do fundo para o carrossel infinito
  bg_x = 0

  rodando = True
  while rodando:
    CLOCK.tick(FPS)

    # --------------------------------------
    # 1. PROCESSAMENTO DE EVENTOS
    # --------------------------------------
    for evento in pygame.event.get():
      if evento.type == pygame.QUIT:
        pygame.quit()
        sys.exit()

      if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
        mouse_pos = pygame.mouse.get_pos()
        if estado == "MENU":
          # Delimitação aproximada dos botões na calçada da tela de menu
          if 70 <= mouse_pos[x := 0] < 350 and 500 <= mouse_pos[1] <= 550:
            estado = "CONTROLES"  # Botão Controles (esq)
          elif 400 <= mouse_pos[0] < 600 and 500 <= mouse_pos[1] <= 550:
            estado = "JOGANDO"  # Botão Jogar (centro)
            # Resetar jogo
            pontos = 0
            velocidade_jogo = 6
            gato.rect.y = gato.chao_y
            grupo_obstaculos.empty()
          elif 650 <= mouse_pos[0] < 930 and 500 <= mouse_pos[1] <= 550:
            estado = "SOBRE"  # Botão Sobre (dir)

        elif estado in ["CONTROLES", "SOBRE", "GAME_OVER", "VITORIA"]:
          # Botão Voltar unificado na calçada inferior
          if 350 <= mouse_pos[0] <= 650 and 500 <= mouse_pos[1] <= 550:
            estado = "MENU"

      if evento.type == pygame.KEYDOWN:
        if estado == "JOGANDO":
          if evento.key in [pygame.K_SPACE, pygame.K_UP]:
            gato.pular()
          if evento.key in [pygame.K_DOWN, pygame.K_LCTRL]:
            gato.abaixado = True
        elif estado in ["GAME_OVER", "VITORIA"]:
          if evento.key == pygame.K_RETURN:
            estado = "MENU"

      if evento.type == pygame.KEYUP:
        if estado == "JOGANDO":
          if evento.key in [pygame.K_DOWN, pygame.K_LCTRL]:
            gato.abaixado = False

      if evento.type == SPAWN_OBSTACULO and estado == "JOGANDO":
        tipo_escolhido = random.choice(["lixeira", "hidrante", "pug_aviao"])
        grupo_obstaculos.add(Obstaculo(tipo_escolhido))

    # --------------------------------------
    # 2. ATUALIZAÇÃO DA LÓGICA (JOGANDO)
    # --------------------------------------
    if estado == "JOGANDO":
      pontos += 1
      if pontos % 200 == 0:
        velocidade_jogo += 1  # Aumenta dificuldade gradualmente

      # Condição de Vitória (1000 pontos)
      if pontos >= 1000:
        estado = "VITORIA"

      # Carrossel do Cenário
      bg_x -= velocidade_jogo
      if bg_x <= -LARGURA:
        bg_x = 0

      grupo_gato.update()
      grupo_obstaculos.update(velocidade_jogo)

      # Colisão (Hit-kill)
      if pygame.sprite.spritecollideany(gato, grupo_obstaculos):
        estado = "GAME_OVER"

    # --------------------------------------
    # 3. RENDERIZAÇÃO NA TELA
    # --------------------------------------
    TELA.fill((0, 0, 0))

    if estado == "MENU":
      TELA.blit(img_menu, (0, 0))

    elif estado == "CONTROLES":
      TELA.blit(img_controles, (0, 0))

    elif estado == "SOBRE":
      TELA.blit(img_sobre, (0, 0))

    elif estado == "JOGANDO":
      # Desenha fundo em loop contínuo
      TELA.blit(img_cenario, (bg_x, 0))
      TELA.blit(img_cenario, (bg_x + LARGURA, 0))

      grupo_gato.draw(TELA)
      grupo_obstaculos.draw(TELA)

      # Placar na tela
      fonte_placar = pygame.font.SysFont("Arial", 26, bold=True)
      texto_pontos = fonte_placar.render(
          f"PONTOS: {pontos} / 1000", True, (255, 255, 255)
      )
      TELA.blit(texto_pontos, (30, 20))

    elif estado == "GAME_OVER":
      TELA.blit(img_gameover, (0, 0))

    elif estado == "VITORIA":
      TELA.blit(img_vitoria, (0, 0))

    pygame.display.flip()


if __name__ == "__main__":
  main()