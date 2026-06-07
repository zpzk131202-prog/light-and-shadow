import math
import tkinter as tk


VIEW_W = 1280
VIEW_H = 720
SCALE = 4
W = VIEW_W // SCALE
H = VIEW_H // SCALE

AMBIENT = 0.14
MAX_LIGHT = 1.35
CONE_ANGLE = math.radians(42)
LIGHT_RANGE = 285


OBSTACLES = (
    (20, 76, 108, 129),
    (143, 44, 205, 129),
    (226, 51, 309, 129),
    (218, 100, 252, 129),
)


class RealLightScene:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Real Light")
        self.canvas = tk.Canvas(self.root, width=VIEW_W, height=VIEW_H, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self.light = [144.0, 76.0]
        self.target = [216.0, 111.0]
        self.dragging = None
        self.drag_start = None
        self.start_light = None
        self.start_target = None
        self.photo = tk.PhotoImage(width=W, height=H)

        self.canvas.create_image(0, 0, image=self.photo, anchor="nw")
        self.canvas.scale("all", 0, 0, SCALE, SCALE)

        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonPress-3>", self.on_pan_press)
        self.canvas.bind("<B3-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<ButtonRelease-3>", self.on_release)
        self.root.bind("<Escape>", lambda _event: self.root.destroy())
        self.root.bind("<Left>", lambda _event: self.nudge_light(-7, 0))
        self.root.bind("<Right>", lambda _event: self.nudge_light(7, 0))
        self.root.bind("<Up>", lambda _event: self.nudge_light(0, -7))
        self.root.bind("<Down>", lambda _event: self.nudge_light(0, 7))
        self.root.bind("a", lambda _event: self.nudge_target(-8, 0))
        self.root.bind("d", lambda _event: self.nudge_target(8, 0))
        self.root.bind("w", lambda _event: self.nudge_target(0, -8))
        self.root.bind("s", lambda _event: self.nudge_target(0, 8))
        self.root.bind("<space>", lambda _event: self.center_light())

    def run(self):
        self.draw()
        self.root.mainloop()

    def on_press(self, event):
        x = event.x / SCALE
        y = event.y / SCALE
        self.drag_start = [x, y]
        self.start_light = self.light[:]
        self.start_target = self.target[:]
        if distance((x, y), self.light) < 28:
            self.dragging = "light"
        elif distance((x, y), self.target) < 28:
            self.dragging = "target"
        else:
            self.dragging = "target"
            self.target[:] = [x, y]
        self.draw()

    def on_pan_press(self, event):
        x = event.x / SCALE
        y = event.y / SCALE
        self.dragging = "beam"
        self.drag_start = [x, y]
        self.start_light = self.light[:]
        self.start_target = self.target[:]

    def on_drag(self, event):
        x = clamp(event.x / SCALE, 0, W - 1)
        y = clamp(event.y / SCALE, 0, H - 1)
        if self.dragging == "light":
            self.light[:] = [x, y]
        elif self.dragging == "target":
            self.target[:] = [x, y]
        elif self.dragging == "beam":
            dx = x - self.drag_start[0]
            dy = y - self.drag_start[1]
            self.light[:] = [clamp(self.start_light[0] + dx, 0, W - 1), clamp(self.start_light[1] + dy, 0, H - 1)]
            self.target[:] = [clamp(self.start_target[0] + dx, 0, W - 1), clamp(self.start_target[1] + dy, 0, H - 1)]
        self.draw()

    def on_release(self, _event):
        self.dragging = None

    def nudge_light(self, dx, dy):
        self.light[:] = [clamp(self.light[0] + dx, 0, W - 1), clamp(self.light[1] + dy, 0, H - 1)]
        self.draw()

    def nudge_target(self, dx, dy):
        self.target[:] = [clamp(self.target[0] + dx, 0, W - 1), clamp(self.target[1] + dy, 0, H - 1)]
        self.draw()

    def center_light(self):
        self.light[:] = [W * 0.45, H * 0.42]
        self.target[:] = [W * 0.68, H * 0.56]
        self.draw()

    def draw(self):
        pixels = []
        aim = math.atan2(self.target[1] - self.light[1], self.target[0] - self.light[0])

        for y in range(H):
            row = []
            for x in range(W):
                base = room_color(x, y)
                light = self.light_amount(x, y, aim)
                row.append(to_hex(apply_light(base, light)))
            pixels.append("{" + " ".join(row) + "}")

        self.photo.put(" ".join(pixels))
        self.draw_handles()

    def light_amount(self, x, y, aim):
        lx, ly = self.light
        dx = x - lx
        dy = y - ly
        dist = math.hypot(dx, dy)
        if dist > LIGHT_RANGE:
            return AMBIENT

        angle = math.atan2(dy, dx)
        delta = abs(wrap_angle(angle - aim))
        if delta > CONE_ANGLE:
            return AMBIENT

        if blocked(lx, ly, x, y):
            return AMBIENT * 0.72

        cone_softness = 1.0 - (delta / CONE_ANGLE) ** 1.7
        falloff = max(0.0, 1.0 - dist / LIGHT_RANGE) ** 1.55
        warmth = MAX_LIGHT * falloff * (0.22 + cone_softness * 0.78)
        return min(1.7, AMBIENT + warmth)

    def draw_handles(self):
        self.canvas.delete("ui")
        lx, ly = self.light[0] * SCALE, self.light[1] * SCALE
        tx, ty = self.target[0] * SCALE, self.target[1] * SCALE

        self.canvas.create_line(lx, ly, tx, ty, fill="#d8d8d8", dash=(4, 5), width=1, tags="ui")
        self.canvas.create_rectangle(lx - 12, ly - 12, lx + 12, ly + 12, fill="#f6f6f6", outline="#222", width=2, tags="ui")
        self.canvas.create_oval(lx - 4, ly - 4, lx + 4, ly + 4, fill="#111", outline="", tags="ui")
        self.canvas.create_rectangle(tx - 13, ty - 13, tx + 13, ty + 13, fill="#f6f6f6", outline="#222", width=2, tags="ui")
        self.canvas.create_line(tx - 8, ty, tx + 8, ty, fill="#111", width=2, tags="ui")
        self.canvas.create_line(tx, ty - 8, tx, ty + 8, fill="#111", width=2, tags="ui")
        self.canvas.create_text(
            18,
            VIEW_H - 20,
            anchor="w",
            text="Left drag: move light or aim. Right drag: move whole beam. Arrows move light, WASD aim, Space reset, Esc quit.",
            fill="#e9e1d2",
            font=("Segoe UI", 12),
            tags="ui",
        )


def room_color(x, y):
    if y >= 129:
        stripe = ((x + y * 2) // 13) % 2
        return (47 + stripe * 12, 29 + stripe * 7, 22 + stripe * 4)

    color = (31, 25, 23)

    if 2 < x < 318 and y in (128, 129):
        return (70, 45, 35)

    for rect in OBSTACLES:
        if inside_rect(x, y, rect):
            return obstacle_color(x, y, rect)

    if 160 <= x <= 199 and 21 <= y <= 82:
        if x in (160, 199) or y in (21, 82):
            return (100, 74, 58)
        cross = abs((x - 160) - (y - 21)) < 2 or abs((x - 199) + (y - 21) - 60) < 2
        if cross:
            return (26, 23, 20)
        return (104, 93, 66)

    if 7 <= x <= 110 and 44 <= y <= 47:
        return (74, 35, 29)
    if 242 <= x <= 307 and 29 <= y <= 35:
        return (43, 38, 32)

    return color


def obstacle_color(x, y, rect):
    x1, y1, x2, y2 = rect
    if x in (x1, x2 - 1) or y in (y1, y2 - 1):
        return (112, 80, 61)
    grain = ((x * 3 + y * 5) % 17) / 17
    return (42 + int(grain * 16), 29 + int(grain * 10), 24 + int(grain * 7))


def blocked(lx, ly, x, y):
    for rect in OBSTACLES:
        if inside_rect(x, y, rect):
            continue
        if segment_intersects_rect(lx, ly, x, y, rect):
            return True
    return False


def segment_intersects_rect(x1, y1, x2, y2, rect):
    rx1, ry1, rx2, ry2 = rect
    if line_intersects_line(x1, y1, x2, y2, rx1, ry1, rx2, ry1):
        return True
    if line_intersects_line(x1, y1, x2, y2, rx2, ry1, rx2, ry2):
        return True
    if line_intersects_line(x1, y1, x2, y2, rx2, ry2, rx1, ry2):
        return True
    if line_intersects_line(x1, y1, x2, y2, rx1, ry2, rx1, ry1):
        return True
    return False


def line_intersects_line(ax, ay, bx, by, cx, cy, dx, dy):
    den = (ax - bx) * (cy - dy) - (ay - by) * (cx - dx)
    if abs(den) < 0.00001:
        return False
    t = ((ax - cx) * (cy - dy) - (ay - cy) * (cx - dx)) / den
    u = -((ax - bx) * (ay - cy) - (ay - by) * (ax - cx)) / den
    return 0 <= t <= 1 and 0 <= u <= 1


def apply_light(rgb, light):
    warm = (255, 210, 118)
    lit = []
    for value, tint in zip(rgb, warm):
        raised = value * light + tint * max(0.0, light - 1.0) * 0.38
        lit.append(int(clamp(raised, 0, 255)))
    return tuple(lit)


def to_hex(rgb):
    return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"


def inside_rect(x, y, rect):
    x1, y1, x2, y2 = rect
    return x1 <= x < x2 and y1 <= y < y2


def wrap_angle(angle):
    while angle > math.pi:
        angle -= math.tau
    while angle < -math.pi:
        angle += math.tau
    return angle


def distance(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def clamp(value, low, high):
    return max(low, min(high, value))


if __name__ == "__main__":
    RealLightScene().run()
