"""Make the shoe images of the catalog: one SVG file for each product and color.

Run `python -m src.shop.make_images` after a change of `site/assets/data/products.json`.
"""

import json
from pathlib import Path

SITE = Path(__file__).resolve().parent / "site"

def shade(color, amount):
    """Make a color darker (amount < 0) or lighter (amount > 0)."""
    h = color.lstrip("#")
    rgb = [int(h[i:i + 2], 16) for i in (0, 2, 4)]
    if amount < 0:
        rgb = [int(c * (1 + amount)) for c in rgb]
    else:
        rgb = [int(c + (255 - c) * amount) for c in rgb]
    return "#{:02x}{:02x}{:02x}".format(*rgb)

def runner(c):
    u, a, s = c["upper"], c["accent"], c["sole"]
    return f'''
<path d="M58 262 Q52 286 82 288 L392 288 Q430 288 432 262 Z" fill="{shade(s,-0.55)}"/>
<path d="M54 238 Q46 264 76 270 L398 270 Q434 268 434 246 Q432 226 404 224 L86 226 Q58 226 54 238 Z" fill="{s}"/>
<path d="M60 258 L430 252" stroke="{shade(s,-0.18)}" stroke-width="3" fill="none"/>
<path d="M68 230 C62 196 72 160 96 146 C114 136 134 132 152 120 L212 86 C228 78 246 82 254 96 L272 130 C302 146 354 168 394 186 C422 198 434 214 428 228 Z" fill="{u}"/>
<path d="M332 170 C372 184 420 200 428 228 L344 230 C338 206 334 188 332 170 Z" fill="{shade(u,-0.18)}"/>
<path d="M68 230 C62 196 72 160 96 146 C112 140 126 152 128 178 C130 204 122 222 120 230 Z" fill="{a}"/>
<path d="M150 214 C196 196 246 168 306 150 L318 164 C258 182 210 208 168 228 Z" fill="{a}"/>
<path d="M96 146 C120 152 150 142 172 128" stroke="{shade(u,-0.35)}" stroke-width="5" fill="none" stroke-linecap="round"/>
<path d="M208 88 C214 68 238 62 250 78 L256 94" fill="{shade(u,0.15)}"/>
<g stroke="{shade(a,0.3) if a != '#ffffff' else '#dddddd'}" stroke-width="5" stroke-linecap="round">
<path d="M214 104 L234 96"/><path d="M226 120 L248 110"/><path d="M240 136 L262 124"/><path d="M256 150 L276 138"/></g>'''

def boot(c):
    u, a, s = c["upper"], c["accent"], c["sole"]
    lugs = "".join(f'<rect x="{x}" y="286" width="18" height="8" rx="2" fill="{shade(s,-0.3)}"/>'
                   for x in range(84, 400, 34))
    return f'''
<path d="M54 266 Q50 292 80 292 L396 292 Q432 292 434 266 Z" fill="{s}"/>{lugs}
<path d="M50 244 Q44 270 72 274 L400 274 Q436 272 436 250 Q434 230 406 228 L84 230 Q54 230 50 244 Z" fill="{shade(s,0.25)}"/>
<path d="M64 236 C60 190 68 120 76 86 C80 70 92 62 108 62 L198 60 C216 60 226 72 224 90 L228 140 C264 160 332 178 386 194 C418 204 434 220 430 234 Z" fill="{u}"/>
<path d="M318 180 C370 192 422 204 430 234 L328 236 C320 214 318 198 318 180 Z" fill="{shade(u,-0.22)}"/>
<path d="M64 236 C60 200 64 160 70 130 L122 136 C120 180 120 214 124 236 Z" fill="{shade(u,-0.22)}"/>
<path d="M76 86 C78 70 92 60 108 60 L198 58 C216 58 228 70 226 90 L214 98 C212 84 202 78 190 78 L110 80 C96 80 88 86 88 100 Z" fill="{a}"/>
<path d="M140 150 C190 150 240 160 300 178" stroke="{a}" stroke-width="7" fill="none" stroke-linecap="round"/>
<g fill="{shade(a,-0.2)}"><circle cx="206" cy="100" r="5"/><circle cx="212" cy="120" r="5"/><circle cx="220" cy="140" r="5"/><circle cx="236" cy="156" r="5"/><circle cx="254" cy="168" r="5"/></g>
<path d="M200 96 L214 118 L204 124 L222 140 L210 146 L238 158 L232 164 L256 170" stroke="{shade(a,0.35)}" stroke-width="4" fill="none" stroke-linejoin="round"/>'''

def court(c):
    u, a, s = c["upper"], c["accent"], c["sole"]
    return f'''
<path d="M54 248 L54 272 Q54 286 72 286 L402 286 Q430 286 430 262 L430 248 Z" fill="{s}"/>
<path d="M54 262 L430 262" stroke="{shade(s,-0.12)}" stroke-width="3"/>
<path d="M62 252 C58 214 68 182 96 170 L172 150 C188 128 208 116 230 116 C250 116 264 128 272 146 C312 162 372 182 406 204 C426 216 430 236 428 252 Z" fill="{u}"/>
<path d="M356 186 C394 200 426 222 428 252 L352 252 C346 228 348 206 356 186 Z" fill="{shade(u,-0.1) if u.lower() not in ('#f4f2ee','#ece6d8') else '#e4ded2'}"/>
<path d="M62 252 C58 220 64 196 80 182 L118 186 C114 210 114 236 118 252 Z" fill="{a}"/>
<path d="M150 230 C200 206 250 186 320 176" stroke="{a}" stroke-width="6" fill="none" stroke-linecap="round" opacity="0.9"/>
<g fill="{shade(u,-0.35)}"><circle cx="196" cy="144" r="4.5"/><circle cx="214" cy="152" r="4.5"/><circle cx="232" cy="160" r="4.5"/><circle cx="250" cy="168" r="4.5"/><circle cx="268" cy="176" r="4.5"/></g>
<g stroke="{shade(u,0.6)}" stroke-width="4" stroke-linecap="round"><path d="M196 144 L214 136"/><path d="M214 152 L232 144"/><path d="M232 160 L250 152"/><path d="M250 168 L268 160"/></g>'''

def slipon(c):
    u, a, s = c["upper"], c["accent"], c["sole"]
    return f'''
<path d="M56 252 L56 270 Q56 284 74 284 L400 284 Q428 284 428 262 L428 252 Z" fill="{s}"/>
<path d="M56 266 L428 266" stroke="{shade(s,-0.15)}" stroke-width="3" stroke-dasharray="6 6"/>
<path d="M64 254 C60 220 70 196 96 186 C140 176 180 170 216 166 C250 162 280 170 320 184 C368 200 412 214 426 236 C430 244 430 250 428 254 Z" fill="{u}"/>
<path d="M150 178 C176 158 214 152 246 164 L240 178 C214 170 184 172 160 186 Z" fill="{a}"/>
<path d="M330 188 C372 202 414 218 426 244" stroke="{shade(u,-0.25)}" stroke-width="3" fill="none"/>
<path d="M66 250 C62 222 70 200 90 190" stroke="{shade(u,-0.3)}" stroke-width="5" fill="none" stroke-linecap="round"/>'''

def oxford(c):
    u, a, s = c["upper"], c["accent"], c["sole"]
    return f'''
<path d="M70 256 L70 288 L138 288 L138 266 L404 266 Q432 264 434 250 L434 244 L150 250 Z" fill="{s}"/>
<path d="M72 254 C68 222 80 198 110 190 L200 178 C232 172 264 176 292 186 C342 200 404 214 426 230 C438 238 436 250 426 252 Z" fill="{u}"/>
<path d="M330 196 C360 204 404 214 426 230 C438 238 436 250 426 252 L340 252 C334 232 332 212 330 196 Z" fill="{shade(u,-0.12)}"/>
<path d="M330 196 C334 214 336 234 340 252" stroke="{a}" stroke-width="3" fill="none"/>
<path d="M200 178 C214 196 250 200 286 186" stroke="{a}" stroke-width="3" fill="none"/>
<g stroke="{shade(u,0.45)}" stroke-width="3" stroke-linecap="round"><path d="M222 186 L240 182"/><path d="M230 192 L250 186"/><path d="M240 196 L262 190"/></g>
<path d="M74 252 C70 226 80 204 104 194" stroke="{shade(u,0.25)}" stroke-width="4" fill="none" opacity="0.6"/>'''

def chelsea(c):
    u, a, s = c["upper"], c["accent"], c["sole"]
    return f'''
<path d="M70 258 L70 290 L140 290 L140 268 L404 268 Q434 266 436 250 L436 246 L150 252 Z" fill="{s}"/>
<path d="M76 256 C72 210 78 130 86 76 C88 64 98 58 110 58 L196 58 C208 58 216 66 214 78 L210 150 C254 170 334 194 398 210 C428 218 440 236 432 252 L428 256 Z" fill="{u}"/>
<path d="M132 70 L188 70 L178 168 C160 176 142 176 126 170 Z" fill="{a}"/>
<g stroke="{shade(a,0.25)}" stroke-width="2"><path d="M140 80 L136 160"/><path d="M152 80 L150 166"/><path d="M164 80 L164 166"/><path d="M176 80 L174 162"/></g>
<path d="M96 58 L90 30 L118 30 L120 58" fill="{shade(u,-0.2)}"/>
<path d="M330 200 C372 210 420 222 432 246" stroke="{shade(u,-0.25)}" stroke-width="3" fill="none"/>'''

SHAPES = dict(runner=runner, boot=boot, court=court, slipon=slipon, oxford=oxford, chelsea=chelsea)


def image(product, color):
    body = SHAPES[product["shape"]](color)
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 480 340" role="img">'
        f'<title>{product["name"]}, {color["name"]}</title>\n'
        '<ellipse cx="244" cy="300" rx="196" ry="13" fill="#000" opacity="0.10"/>'
        f"{body}\n</svg>\n"
    )


def main():
    products = json.loads((SITE / "assets/data/products.json").read_text(encoding="utf-8"))
    out = SITE / "assets/img"
    out.mkdir(exist_ok=True)
    for product in products:
        for color in product["colors"]:
            name = color["name"].lower().replace(" ", "-")
            (out / f'{product["id"]}-{name}.svg').write_text(image(product, color), encoding="utf-8")


if __name__ == "__main__":
    main()
