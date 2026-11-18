#!/bin/zsh
set -eu
cd "${0:A:h}/.."
if [[ ! -x backend/.venv-ai/bin/python ]]; then
  print -u2 'Ambiente backend/.venv-ai não encontrado. Consulte o README.'
  exit 1
fi
if [[ -z ${AWS_BEARER_TOKEN_BEDROCK:-} ]]; then
  if [[ ! -t 0 ]]; then
    print -u2 'Abra um terminal interativo para informar a chave.'
    exit 1
  fi
  saved_tty=$(stty -g)
  trap 'stty "$saved_tty"' EXIT INT TERM
  stty -icanon -echo min 1 time 0
  print -n 'Cole a chave temporária do Bedrock e pressione Enter: '
  IFS= read -r AWS_BEARER_TOKEN_BEDROCK
  stty "$saved_tty"
  trap - EXIT INT TERM
  print
  export AWS_BEARER_TOKEN_BEDROCK
fi
if [[ -z ${AWS_BEARER_TOKEN_BEDROCK} ]]; then
  print -u2 'Nenhuma chave informada.'
  exit 1
fi
export AWS_REGION=${AWS_REGION:-us-east-1}
export BEDROCK_MODEL_ID=${BEDROCK_MODEL_ID:-us.anthropic.claude-haiku-4-5-20251001-v1:0}
exec backend/.venv-ai/bin/python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
