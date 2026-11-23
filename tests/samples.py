"""Builders for test inputs. Everything is generated at test time and is inert:
the "malicious" samples only carry the names and structure the tools look for."""

import base64
import gzip
import io
import tarfile
import zipfile
import zlib


def pdf(text: str = "Hello quarantine", catalog_extra: str = "", extra_objects: tuple[str | bytes, ...] = (),
        font: str = "Helvetica", content: bytes | None = None, pages: int = 1) -> bytes:
    """A small PDF. `content` replaces the page's drawing instructions; `pages` repeats the page."""
    if content is None:
        content = f"BT /F1 18 Tf 20 100 Td ({text}) Tj ET".encode()
    kids = " ".join(f"{3 + i} 0 R" for i in range(pages))
    first_extra = 3 + pages                     # object numbers: 1 catalog, 2 page tree, then the pages
    page = (b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 200] /Contents %d 0 R "
            b"/Resources << /Font << /F1 %d 0 R >> >> >>" % (first_extra, first_extra + 1))
    objects = [
        f"<< /Type /Catalog /Pages 2 0 R {catalog_extra} >>".encode(),
        f"<< /Type /Pages /Kids [{kids}] /Count {pages} >>".encode(),
        *[page] * pages,
        b"<< /Length %d >>\nstream\n%s\nendstream" % (len(content), content),
        f"<< /Type /Font /Subtype /Type1 /BaseFont /{font} >>".encode(),
        *[o if isinstance(o, bytes) else o.encode() for o in extra_objects],
    ]
    out = io.BytesIO()
    out.write(b"%PDF-1.4\n")
    offsets = []
    for i, body in enumerate(objects, start=1):
        offsets.append(out.tell())
        out.write(b"%d 0 obj\n%s\nendobj\n" % (i, body))
    xref = out.tell()
    out.write(b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1))
    for off in offsets:
        out.write(b"%010d 00000 n \n" % off)
    out.write(b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objects) + 1, xref))
    return out.getvalue()


def pdf_with_script() -> bytes:
    """A PDF whose catalog has an open action pointing at a (harmless) script object."""
    return pdf(catalog_extra="/OpenAction 6 0 R",
               extra_objects=("<< /Type /Action /S /JavaScript /JS (1+1;) >>",))


def pdf_with_attachment() -> bytes:
    """An attached file whose stream leaves out the optional "/Type /EmbeddedFile"."""
    return pdf(catalog_extra="/Names << /EmbeddedFiles << /Names [(note.txt) 6 0 R] >> >>",
               extra_objects=("<< /Type /Filespec /F (note.txt) /EF << /F 7 0 R >> >>",
                              "<< /Length 2 >>\nstream\nhi\nendstream"))


def unexpandable_stream() -> bytes:
    """A PDF object that is never used and unpacks to about 105 MB of zeros. mutool refuses to
    expand it, and a file must not be able to switch off the deep scan that way."""
    packed = zlib.compress(zlib.compress(bytes(105 * 1024 * 1024)))
    return b"<< /Length %d /Filter [/FlateDecode /FlateDecode] >>\nstream\n%s\nendstream" % (len(packed), packed)


_CONTENT_TYPES = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
    '<Default Extension="xml" ContentType="application/xml"/>'
    '<Override PartName="/word/document.xml" ContentType='
    '"application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
    "</Types>"
)
_RELS = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" Type='
    '"http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
    'Target="word/document.xml"/></Relationships>'
)
_REMOTE_TEMPLATE_RELS = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" Type='
    '"http://schemas.openxmlformats.org/officeDocument/2006/relationships/attachedTemplate" '
    'Target="http://example.invalid/template.dotm" TargetMode="External"/></Relationships>'
)
_LINK_RELS = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" Type='
    '"http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink" '
    'Target="http://example.invalid/page" TargetMode="External"/></Relationships>'
)


def docx(text: str = "Hello from docx", macros: bool = False, remote_template: bool = False,
         link: bool = False) -> bytes:
    document = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body><w:p><w:r><w:t>{text}</w:t></w:r></w:p></w:body></w:document>"
    )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", _CONTENT_TYPES)
        z.writestr("_rels/.rels", _RELS)
        z.writestr("word/document.xml", document)
        if macros:
            z.writestr("word/vbaProject.bin", b"placeholder, not a real macro project")
        if remote_template:
            z.writestr("word/_rels/settings.xml.rels", _REMOTE_TEMPLATE_RELS)
        if link:
            z.writestr("word/_rels/document.xml.rels", _LINK_RELS)
    return buf.getvalue()


def tar_gz(members: dict[str, bytes], symlinks: dict[str, str] | None = None,
           executable: tuple[str, ...] = (), folders: dict[str, int] | None = None,
           pipes: tuple[str, ...] = ()) -> bytes:
    """`folders` maps a folder name to its permission bits; list it before the members inside it."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as t:
        for name, mode in (folders or {}).items():
            info = tarfile.TarInfo(name)
            info.type = tarfile.DIRTYPE
            info.mode = mode
            t.addfile(info)
        for name, data in members.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            info.mode = 0o755 if name in executable else 0o644
            t.addfile(info, io.BytesIO(data))
        for name, target in (symlinks or {}).items():
            info = tarfile.TarInfo(name)
            info.type = tarfile.SYMTYPE
            info.linkname = target
            t.addfile(info)
        for name in pipes:
            info = tarfile.TarInfo(name)
            info.type = tarfile.FIFOTYPE
            t.addfile(info)
    return buf.getvalue()


def tar_gz_of_zeros(size: int) -> bytes:
    """A small .tar.gz holding one file of `size` zero bytes. It is put together from one compressed
    block repeated many times, so building it takes a moment however large `size` is.
    The owner name has a space in it: that shifts the columns of a verbose listing, which is why
    the size of an archive is measured and not read from that listing."""
    block = 64 * 1024 * 1024
    assert size % block == 0
    info = tarfile.TarInfo("zeros.bin")
    info.size = size
    info.uname = "some user"
    return gzip.compress(info.tobuf()) + gzip.compress(bytes(block)) * (size // block) + gzip.compress(bytes(1024))


def zip_bytes(members: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in members.items():
            z.writestr(name, data)
    return buf.getvalue()


DESKTOP_LAUNCHER = b"[Desktop Entry]\nType=Application\nName=Invoice\nExec=sh -c 'echo launcher'\n"
URL_SHORTCUT = b"[InternetShortcut]\nURL=http://example.invalid/\n"
HELP_FILE = b"ITSF\x03\x00\x00\x00\x60\x00\x00\x00\x01\x00\x00\x00" + bytes(200)   # header of a Windows .chm
SVG = b'<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"><rect width="10" height="10"/></svg>\n'
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
RTF = rb"{\rtf1\ansi Hello from rtf\par}"
RTF_WITH_OBJECT = rb"{\rtf1\ansi Text{\object\objemb{\*\objdata 00}}\par}"       # an empty object, nothing in it
WEBP = base64.b64decode("UklGRhoAAABXRUJQVlA4TA0AAAAvAAAAEAcQERGIiP4HAA==")       # one transparent pixel
