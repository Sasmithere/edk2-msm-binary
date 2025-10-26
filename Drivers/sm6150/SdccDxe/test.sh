#!/bin/bash
set -e
BUILD_DIR="$1"
if [ -z "$BUILD_DIR" ]; then
  echo "Usage: $0 <path-to-module-build-dir-containing-objects-and-dll>"
  exit 1
fi

# find object files related to SdccDxe; adjust the grep if needed
OBJS=$(find "$BUILD_DIR" -type f -name '*.o' -path '*SdccDxe*' || true)
if [ -z "$OBJS" ]; then
  echo "No object files found for SdccDxe in $BUILD_DIR. You may need to point to OBJECTS_* folder."
  exit 1
fi

OUT="$BUILD_DIR/SdccDxe.efi"
echo "Relinking into $OUT with 64K section alignment..."
# Use clang/ld.lld or your platform linker
clang -target aarch64-none-elf -Wl,--section-alignment=0x10000 -nostdlib $OBJS -o "$OUT" || {
  echo "Manual link failed; try using platform-specific linker and linker script."
  exit 2
}

echo "Verifying..."
llvm-readelf -h "$OUT" | grep -i align || true
llvm-readelf -S "$OUT" | grep -i debug || true
if command -v DumpImage >/dev/null 2>&1; then
  DumpImage -f "$OUT"
fi
echo "Done."

