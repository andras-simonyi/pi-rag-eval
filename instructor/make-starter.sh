#!/usr/bin/env bash
#
# make-starter.sh — produce a stripped copy of this repo for the bootstrap track.
#
# The full repo hands students finished skills, scripts and templates. This
# builds a variant with the generated artifacts removed, so they produce them
# with Pi instead. The originals are kept alongside as *.shipped.* so students
# can diff their version against them.
#
#   ./instructor/make-starter.sh ../pi-rag-eval-starter
#
# Budget an extra 45-60 minutes of session time if you hand this out.

set -euo pipefail

DEST="${1:-../pi-rag-eval-starter}"

if [[ -e "$DEST" ]]; then
  echo "Refusing to overwrite $DEST" >&2
  exit 1
fi

echo "--> copying to $DEST"
mkdir -p "$DEST"
tar --exclude='.git' --exclude='__pycache__' --exclude='*.pyc' -cf - . | tar -xf - -C "$DEST"

cd "$DEST"

echo "--> setting aside the generated artifacts"
mv AGENTS.md                    AGENTS.shipped.md
mv TODO.template.md             TODO.shipped.md
mv tools/run_sweep.py           tools/run_sweep.shipped.py
mv .agents/skills/corpus-eval   .agents/skills/corpus-eval.shipped

cat > STARTER.md <<'INNER'
# Starter variant

Four things that exist in the finished repo have been set aside here, because
you are going to generate them:

| Missing | You will write it in | Reference copy |
|---|---|---|
| `AGENTS.md` | `prompts/bootstrap/b1-agents-md.md` | `AGENTS.shipped.md` |
| `tools/run_sweep.py` | `prompts/bootstrap/b2-script.md` | `tools/run_sweep.shipped.py` |
| `TODO.template.md` | `prompts/bootstrap/b4-todo.md` | `TODO.shipped.md` |
| the `corpus-eval` skill | `prompts/bootstrap/b3-skill.md` | `.agents/skills/corpus-eval.shipped/` |

Do not read the `.shipped` versions until after you have written yours. The
comparison only teaches you something if you did the work first.

Two skills remain in place, deliberately: `corpus-search`, because you need the
CLI documented before you can use it, and `skill-writer`, because it is the
tool you will use to write the others.

Note the ordering problem this creates. The `corpus-eval` skill describes a
procedure, and the honest way to write it is to perform the procedure first and
capture what happened. So: run the evaluation the hard way, with the protocol
in front of you, and write the skill at the end. That is the right order for
real skills too, and the finished repo hides it.
INNER

echo
echo "Done. $DEST"
echo "Hand students the starter; keep the full repo as your reference."
