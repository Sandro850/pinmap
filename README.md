# Pinmap

Um site simples para contar visitas no navegador e deixar pins com origem em um mapa.

## Rodar Localmente

Crie/ative um ambiente virtual, instale as dependencias e rode o Flask:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Abra:

```text
http://localhost:5000
```

## Testar a API

Listar pins aprovados:

```bash
curl http://localhost:5000/api/pins
```

Criar um pin:

```bash
curl -X POST http://localhost:5000/api/pins \
  -H "Content-Type: application/json" \
  -d '{"origin":"Brasil","lat":-14.235,"lng":-51.9253}'
```

Para testar com Gunicorn localmente:

```bash
gunicorn app:app
```

Abra:

```text
http://localhost:8000
```

## O Que Ele Faz

- Mostra um mapa com Leaflet.
- Permite clicar no mapa ou usar geolocalizacao.
- Salva origem e coordenadas em SQLite.
- Lista pins aprovados.
- Tem i18n simples em `pt-BR`, `en`, `es` e `fr`.
- Usa `localStorage` apenas como fallback se o backend estiver indisponivel.
- Modera `name` e `origin` no backend antes de salvar.

## API

- `GET /api/pins`: lista pins aprovados.
- `POST /api/pins`: cria um pin depois de validar e moderar.

O SQLite fica em `pinmap.db`, criado automaticamente ao iniciar o app.

## Validacao

No `POST /api/pins`, o backend valida:

- `name`: opcional, maximo 40 caracteres, fallback `Visitante anonimo`.
- `origin`: obrigatorio, maximo 80 caracteres.
- `lat`: numero entre -90 e 90.
- `lng`: numero entre -180 e 180.

O `POST /api/pins` tambem:

- exige `Content-Type: application/json`;
- rejeita JSON invalido;
- rejeita campos inesperados;
- rejeita HTML simples em `name` e `origin`;
- ignora `message`, mantendo a coluna apenas por compatibilidade;
- aplica um rate limit simples em memoria por IP.

## Deploy no Render

Crie um novo **Web Service** no Render apontando para este repositorio.

Use:

```bash
pip install -r requirements.txt
```

como **Build Command**.

Use:

```bash
gunicorn app:app
```

como **Start Command**.

Se a plataforma exigir bind explicito na porta, use:

```bash
gunicorn app:app --bind 0.0.0.0:$PORT
```

O app nao depende de `FLASK_DEBUG` em producao. Se quiser debug local, rode:

```bash
FLASK_DEBUG=1 python app.py
```

## Nota Sobre SQLite

SQLite e suficiente para demo, portfolio e aprendizado. Em deploys gratuitos/efemeros, arquivos locais podem ser apagados quando o servico reinicia ou redeploya. Para producao real, prefira PostgreSQL, Supabase ou outro banco persistente externo.

## Proximos Passos Para Producao Real

- Migrar SQLite para PostgreSQL ou Supabase.
- Adicionar rate limit persistente no proxy/plataforma ou Redis.
- Configurar logs e alertas.
- Configurar backups do banco.
- Usar dominio proprio.
- Criar painel admin somente quando houver necessidade real.

## Estrutura

```text
pinmap/
├── app.py
├── blocked_terms_ptbr.py
├── moderation.py
├── README.md
├── .gitignore
├── requirements.txt
├── pinmap.db              # Criado automaticamente, ignorado pelo Git
├── templates/
│   └── index.html
└── static/
    ├── style.css
    ├── script.js
    ├── i18n.js
    └── assets/
        ├── images/
        └── icons/
```

## Limpeza Local

Use estes comandos apenas em desenvolvimento, antes do site ir ao ar ou quando quiser limpar dados de teste.

Para apagar todos os pins do SQLite e reiniciar os IDs:

```bash
sqlite3 pinmap.db "DELETE FROM pins; DELETE FROM sqlite_sequence WHERE name='pins';"
```

Para limpar o fallback local do navegador, abra o DevTools no site e rode no Console:

```js
localStorage.removeItem("pinmap:pins");
```

Para zerar tambem o contador local de visitas:

```js
localStorage.removeItem("pinmap:visits");
```

Nao existe rota publica para apagar pins, e o site nao exibe botao publico de limpeza.
