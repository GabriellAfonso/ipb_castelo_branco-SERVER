# Bible — Tasks

## Adequação arquitetural

- [x] Criar tipo `BibleBook` (Pydantic model) em vez de `dict[str, Any]`
- [x] Criar `BibleRepository` — responsável por carregar e buscar dados dos JSONs
- [x] Criar `BibleService` — lógica de negócio (listar versões, buscar por nome)
- [x] Criar `BibleVersionNotFound` em `core/domain/exceptions.py`
- [x] Registrar service e repository no DI container (`config/di.py`)
- [x] Refatorar views para chamar service via DI (não importar `BIBLES` direto)
- [x] Atualizar testes para nova estrutura
- [x] Remover `loader.py` (substituído por `repositories.py`)
