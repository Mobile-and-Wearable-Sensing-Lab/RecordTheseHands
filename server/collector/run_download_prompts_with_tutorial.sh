#!/usr/bin/env bash

USERNAME="lenovo_p2"

FILES=(
  "prompts/prompts-PREFIX-2025-11-20T09:36:16.965322+00:00.json"
  "prompts/prompts-PREFIX-2025-11-20T09:41:29.873176+00:00.json"
  "prompts/prompts-PREFIX-2025-11-20T09:41:58.579852+00:00.json"
  "prompts/prompts-PREFIX-2025-11-20T09:42:31.251921+00:00.json"
  "prompts/prompts-PREFIX-2025-11-20T09:43:46.318142+00:00.json"
  "prompts/prompts-PREFIX-2025-11-20T09:44:13.938932+00:00.json"
  "prompts/prompts-PREFIX-2025-11-20T09:44:45.953085+00:00.json"
  "prompts/prompts-PREFIX-2025-11-20T09:45:17.107271+00:00.json"
  "prompts/prompts-PREFIX-2025-11-20T09:45:46.015709+00:00.json"
  "prompts/prompts-PREFIX-2025-11-20T09:46:44.775827+00:00.json"
  "prompts/prompts-PREFIX-2025-11-20T09:47:07.629767+00:00.json"
  "prompts/prompts-PREFIX-2025-11-20T09:47:41.060954+00:00.json"
  "prompts/prompts-PREFIX-2025-11-20T09:48:06.117103+00:00.json"
  "prompts/prompts-PREFIX-2025-11-20T09:48:35.196914+00:00.json"
  "prompts/prompts-PREFIX-2025-11-20T09:48:59.888038+00:00.json"
  "prompts/prompts-PREFIX-2025-11-20T09:49:24.023772+00:00.json"
  "prompts/prompts-PREFIX-2025-11-20T09:50:16.135971+00:00.json"
  "prompts/prompts-PREFIX-2025-11-20T09:50:37.848869+00:00.json"
  "prompts/prompts-PREFIX-2025-11-20T09:51:01.754306+00:00.json"
  "prompts/prompts-PREFIX-2025-11-20T09:51:23.932043+00:00.json"
  "prompts/prompts-PREFIX-2025-11-20T09:51:48.052357+00:00.json"
  "prompts/prompts-PREFIX-2025-11-20T09:52:18.486672+00:00.json"
)

# 1) First prompt
FIRST_FILE="${FILES[0]}"
echo "Downloading FIRST prompt: $FIRST_FILE"
python create_directive.py "$USERNAME" downloadPrompts "$FIRST_FILE"

# 2) Set tutorial mode false (only once)
echo "Setting tutorial mode to false"
python create_directive.py "$USERNAME" setTutorialMode false

# 3) Remaining prompts
for f in "${FILES[@]:1}"; do
  echo "Downloading prompt: $f"
  python create_directive.py "$USERNAME" downloadPrompts "$f"
done

echo "All directives created."
