"""scripts/imp4_resources.py: odmawia zapisu tekstów oryginału do repozytorium; czyta zasoby .resources."""
import importlib.util
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('imp4_resources', ROOT / 'scripts' / 'imp4_resources.py')
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)


def _resources(entries):
    """Minimalny blok .resources w wersji 2 (tylko łańcuchy) — zgodnie z publiczną specyfikacją formatu."""
    def s7(text):
        raw = text.encode('utf-8')
        return bytes([len(raw)]) + raw
    reader = s7('System.Resources.ResourceReader') + s7('System.Resources.RuntimeResourceSet')
    names, data = b'', b''
    positions = []
    for name, value in entries:
        positions.append(len(names))
        raw = name.encode('utf-16-le')
        names += bytes([len(raw)]) + raw + struct.pack('<i', len(data))
        data += b'\x01' + s7(value)
    head = b'\xce\xca\xef\xbe' + struct.pack('<ii', 1, len(reader)) + reader
    body = struct.pack('<iii', 2, len(entries), 0)
    blob = head + body
    blob += b'\x00' * ((-len(blob)) % 8)
    blob += struct.pack(f'<{len(entries)}i', *range(len(entries)))      # skróty nazw (nieużywane)
    blob += struct.pack(f'<{len(entries)}i', *positions)
    data_section = len(blob) + 4 + len(names)
    return blob + struct.pack('<i', data_section) + names + data


def test_reads_texts_and_refuses_repo_folder(tmp_path):
    exe = tmp_path / 'program.exe'
    exe.write_bytes(b'MZ' + b'\x00' * 30 + _resources([('>>$this.Name', 'Okno_Testowe'),
                                                       ('L1.Text', 'Długość LP [mm]:'),
                                                       ('L1.Font', 'Arial')]) + b'\x00' * 16)
    out = tmp_path / 'teksty'
    assert tool.main([str(exe), '--out', str(out)]) == 0
    text = (out / 'Okno_Testowe.txt').read_text(encoding='utf-8')
    assert 'L1.Text\tDługość LP [mm]:' in text and 'Arial' not in text
    assert tool.main([str(exe), '--out', str(ROOT / 'tmp_teksty')]) == 2
    assert not (ROOT / 'tmp_teksty').exists()
