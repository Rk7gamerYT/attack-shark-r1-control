# Contribuir

Abra uma issue com a distribuição, versão do kernel, modelo do mouse e conexão
utilizada. Remova endereços MAC, números de série e outros dados pessoais dos logs.

```bash
./run.sh --demo --smoke-test
.venv/bin/python -m unittest discover -s tests
```

Envie mudanças em pull requests com descrição do comportamento e da validação.
Diferencie testes simulados de validações em hardware real. Não acrescente
comandos de firmware sem evidência do protocolo. Contribuições ao código do app
são disponibilizadas sob a licença MIT do projeto.
