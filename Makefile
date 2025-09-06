.PHONY: dev build test e2e package clean

dev:
	pnpm i
	concurrently \
		"uvicorn services.asr.app:app --reload --port 7031" \
		"uvicorn services.redaction.app:app --reload --port 7032" \
		"uvicorn services.insights_bridge.app:app --reload --port 7033" \
		"pnpm -C apps/desktop/renderer dev" \
		"pnpm -C apps/desktop/electron dev"

build:
	pnpm -C apps/desktop/renderer build
	pnpm -C apps/desktop/electron build

test:
	pytest -q
	pnpm -C apps/desktop/renderer test

e2e:
	pnpm -C apps/desktop/renderer e2e

package:
	pnpm -C apps/desktop/electron build

clean:
	rm -rf node_modules apps/*/node_modules packages/*/node_modules
	rm -rf apps/desktop/renderer/dist apps/desktop/electron/dist