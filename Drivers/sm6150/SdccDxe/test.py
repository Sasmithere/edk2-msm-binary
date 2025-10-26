import pefile
import math
import sys

def align(value, alignment):
    return (value + (alignment - 1)) & ~(alignment - 1)

def realign_pe_sections(pe_path, output_path, alignment=0x10000):
    pe = pefile.PE(pe_path)
    print(f"Original SectionAlignment: {hex(pe.OPTIONAL_HEADER.SectionAlignment)}")

    pe.OPTIONAL_HEADER.SectionAlignment = alignment
    aligned_virtual_address = align(pe.sections[0].VirtualAddress, alignment)

    for i, section in enumerate(pe.sections):
        orig_va = section.VirtualAddress
        orig_vs = section.Misc_VirtualSize
        aligned_va = align(orig_va, alignment)
        aligned_vs = align(orig_vs, alignment)
        print(f"Section {section.Name.decode().strip()} Realign VA: {hex(orig_va)} -> {hex(aligned_va)}, VS: {hex(orig_vs)} -> {hex(aligned_vs)}")

        section.VirtualAddress = aligned_va
        section.Misc_VirtualSize = aligned_vs

        # Adjust PointerToRawData and SizeOfRawData if needed, here naive alignment
        section.PointerToRawData = align(section.PointerToRawData, pe.OPTIONAL_HEADER.FileAlignment)
        section.SizeOfRawData = align(section.SizeOfRawData, pe.OPTIONAL_HEADER.FileAlignment)

        # For next section virtual address calculation:
        if i < len(pe.sections) - 1:
            pe.sections[i+1].VirtualAddress = aligned_va + aligned_vs

    # Align SizeOfImage to section alignment
    size_of_image = pe.sections[-1].VirtualAddress + pe.sections[-1].Misc_VirtualSize
    pe.OPTIONAL_HEADER.SizeOfImage = align(size_of_image, alignment)
    print(f"New SizeOfImage: {hex(pe.OPTIONAL_HEADER.SizeOfImage)}")

    pe.write(output_path)
    print(f"Realigned PE saved to {output_path}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <input_pe> <output_pe>")
        sys.exit(1)

    realign_pe_sections(sys.argv[1], sys.argv[2])

