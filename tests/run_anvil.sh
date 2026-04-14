#!/usr/bin/env bash

set -euo pipefail

CHAIN_ID="${CHAIN_ID:-2017}"
BLOCK_GAS_LIMIT="${BLOCK_GAS_LIMIT:-800000000}"
ANVIL_HARDFORK="${ANVIL_HARDFORK:-osaka}"
ANVIL_HOST="${ANVIL_HOST:-0.0.0.0}"
ANVIL_PORT="${ANVIL_PORT:-8545}"
ANVIL_SLOTS_IN_AN_EPOCH="${ANVIL_SLOTS_IN_AN_EPOCH:-1}"
RPC_URL="http://127.0.0.1:${ANVIL_PORT}"

anvil \
  --host "${ANVIL_HOST}" \
  --port "${ANVIL_PORT}" \
  --chain-id "${CHAIN_ID}" \
  --hardfork "${ANVIL_HARDFORK}" \
  --slots-in-an-epoch "${ANVIL_SLOTS_IN_AN_EPOCH}" \
  --gas-price 0 \
  --block-base-fee-per-gas 0 \
  --gas-limit "${BLOCK_GAS_LIMIT}" &
ANVIL_PID=$!

cleanup() {
  kill "${ANVIL_PID}" 2>/dev/null || true
  wait "${ANVIL_PID}" 2>/dev/null || true
}
trap cleanup INT TERM EXIT

until cast rpc --rpc-url "${RPC_URL}" web3_clientVersion >/dev/null 2>&1; do
  sleep 0.2
done

wait "${ANVIL_PID}"