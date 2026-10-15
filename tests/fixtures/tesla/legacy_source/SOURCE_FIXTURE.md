# Original Tesla source fixture

All 91 files named by MANIFEST.sha256 are preserved byte-for-byte from the
accepted source at commit 5dad4d9 (the eb2e48d audit baseline). This archive
includes the old coupled scripts and complete inputs/outputs for inspection or
an isolated legacy rerun. It is not production framework code.

The original README and handoffs are historical. Their relative paths resolve
inside this directory. Use a separate copy before running those scripts; they
overwrite their own model, validation and export files. No generic framework
module imports or executes this source fixture.

The separate frozen acceptance snapshot under ../baseline is unchanged.
