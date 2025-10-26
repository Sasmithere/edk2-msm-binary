#!/usr/bin/env python3
import os
import subprocess
import shutil
import argparse

def run(cmd, cwd=None, check=True):
    print(f"[*] Running: {' '.join(cmd)}")
    res = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if res.returncode != 0 and check:
        print(f"[!] Command failed:\n{res.stderr}")
        raise RuntimeError(f"Command failed: {' '.join(cmd)}")
    return res.stdout.strip()

def find_sdcc_dxe(root_dir):
    targets = []
    for root, _, files in os.walk(root_dir):
        for f in files:
            if f.lower() in ("sdccdxe.dll", "sdccdxe.efi"):
                targets.append(os.path.join(root, f))
    return targets

def strip_debug(fname):
    stripped = fname.replace(".dll", ".efi") if fname.endswith(".dll") else fname
    stripped_tmp = stripped + ".tmp"
    if shutil.which("llvm-strip"):
        run(["llvm-strip", "--strip-debug", fname, "-o", stripped_tmp])
    else:
        print("[!] llvm-strip not found, skipping strip")
        shutil.copy(fname, stripped_tmp)
    os.replace(stripped_tmp, stripped)
    print(f"[+] Stripped debug symbols → {stripped}")
    return stripped

def verify_alignment(fname):
    try:
        out = run(["llvm-readelf", "-h", fname], check=False)
        for line in out.splitlines():
            if "SectionAlignment" in line or "FileAlignment" in line:
                print("    " + line.strip())
    except FileNotFoundError:
        print("[!] llvm-readelf not found — skipping alignment verification")

def relink(fname, section_align=0x10000):
    dirname = os.path.dirname(fname)
    base = os.path.splitext(os.path.basename(fname))[0]
    new_file = os.path.join(dirname, f"{base}_aligned.efi")

    # gather .o files
    obj_dir = None
    for parent in [dirname, os.path.join(dirname, ".."), os.path.join(dirname, "../..")]:
        if os.path.exists(parent) and any(f.endswith(".o") for f in os.listdir(parent)):
            obj_dir = parent
            break

    if not obj_dir:
        print("[!] No object files found near build directory — cannot relink precisely.")
        print("[!] Falling back to padding method (fake relink).")
        shutil.copy(fname, new_file)
        return new_file

    # Collect object files for SdccDxe
    objs = [os.path.join(obj_dir, f) for f in os.listdir(obj_dir) if f.endswith(".o")]
    if not objs:
        print("[!] No object files found, copying existing file instead.")
        shutil.copy(fname, new_file)
        return new_file

    linker = shutil.which("ld.lld") or shutil.which("aarch64-linux-gnu-ld") or shutil.which("ld")
    if not linker:
        print("[!] No linker found, copying existing file instead.")
        shutil.copy(fname, new_file)
        return new_file

    cmd = [linker, "--section-alignment", str(section_align), "-o", new_file] + objs
    run(cmd)
    print(f"[+] Relinked → {new_file}")
    return new_file

def dump_image_check(fname):
    if shutil.which("DumpImage"):
        print("[*] Validating with DumpImage ...")
        run(["DumpImage", "-f", fname], check=False)
    else:
        print("[!] DumpImage tool not found — skipping validation")

def main():
    parser = argparse.ArgumentParser(description="Fix SdccDxe alignment and format issues.")
    parser.add_argument("build_dir", help="Path to build output (e.g. Build/.../SdccDxe/DEBUG/)")
    parser.add_argument("--strip-only", action="store_true", help="Only strip debug sections, no relink")
    parser.add_argument("--section-align", type=lambda x: int(x, 0), default=0x10000,
                        help="Desired SectionAlignment (default 0x10000)")
    args = parser.parse_args()

    targets = find_sdcc_dxe(args.build_dir)
    if not targets:
        print("[!] No SdccDxe.dll or .efi found under", args.build_dir)
        return

    for target in targets:
        print(f"\n=== Processing {target} ===")
        stripped = strip_debug(target)
        if not args.strip_only:
            aligned = relink(stripped, args.section_align)
        else:
            aligned = stripped
        verify_alignment(aligned)
        dump_image_check(aligned)

if __name__ == "__main__":
    main()

