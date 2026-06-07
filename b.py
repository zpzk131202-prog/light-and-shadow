import math
import tkinter as tk


VIEW_W = 1280
VIEW_H = 720
SCALE = 4
W = VIEW_W // SCALE
H = VIEW_H // SCALE

EPS = 0.001


class Ray3DLight:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Ray Traced 3D Light")
        self.canvas = tk.Canvas(self.root, width=VIEW_W, height=VIEW_H, bg="#050505", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self.photo = tk.PhotoImage(width=W, height=H)
        self.image_id = self.canvas.create_image(0, 0, image=self.photo, anchor="nw")
        self.canvas.scale(self.image_id, 0, 0, SCALE, SCALE)

        self.camera_angle = 0.0
        self.light = [-1.9, 1.7, -1.4]
        self.target = [0.15, 0.75, 1.3]
        self.dragging = None
        self.drag_last = None
        self.dirty = True

        self.root.bind("<Escape>", lambda _event: self.root.destroy())
        self.root.bind("<Left>", lambda _event: self.rotate(-0.08))
        self.root.bind("<Right>", lambda _event: self.rotate(0.08))
        self.root.bind("w", lambda _event: self.move_light_depth(0.18))
        self.root.bind("s", lambda _event: self.move_light_depth(-0.18))
        self.root.bind("a", lambda _event: self.move_light_screen(-24, 0))
        self.root.bind("d", lambda _event: self.move_light_screen(24, 0))
        self.root.bind("<Up>", lambda _event: self.move_light(0.0, 0.18, 0.0))
        self.root.bind("<Down>", lambda _event: self.move_light(0.0, -0.18, 0.0))
        self.root.bind("<space>", lambda _event: self.reset())

        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonPress-3>", self.on_depth_press)
        self.canvas.bind("<B3-Motion>", self.on_drag)
        self.canvas.bind("<MouseWheel>", self.on_wheel)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<ButtonRelease-3>", self.on_release)

    def run(self):
        self.loop()
        self.root.mainloop()

    def loop(self):
        if self.dirty:
            self.render()
            self.dirty = False
        self.root.after(30, self.loop)

    def rotate(self, amount):
        self.camera_angle += amount
        self.dirty = True

    def move_light(self, dx, dy, dz):
        self.light[0] = clamp(self.light[0] + dx, -3.1, 3.1)
        self.light[1] = clamp(self.light[1] + dy, 0.25, 3.3)
        self.light[2] = clamp(self.light[2] + dz, -2.2, 4.8)
        self.dirty = True

    def move_light_screen(self, dx, dy):
        cam_pos, forward, right, up = camera_basis(self.camera_angle)
        del cam_pos, forward
        self.move_light(right[0] * dx * 0.007 + up[0] * -dy * 0.007, right[1] * dx * 0.007 + up[1] * -dy * 0.007, right[2] * dx * 0.007 + up[2] * -dy * 0.007)

    def move_light_depth(self, amount):
        _cam_pos, forward, _right, _up = camera_basis(self.camera_angle)
        self.move_light(forward[0] * amount, forward[1] * amount, forward[2] * amount)

    def reset(self):
        self.camera_angle = 0.0
        self.light[:] = [-1.9, 1.7, -1.4]
        self.target[:] = [0.15, 0.75, 1.3]
        self.dirty = True

    def on_press(self, event):
        lx, ly = self.project_marker(self.light)
        self.drag_last = [event.x, event.y]
        if math.hypot(event.x - lx, event.y - ly) < 34:
            self.dragging = "light"
        else:
            self.dragging = "target"
            self.aim_at_mouse(event.x, event.y)
            self.dirty = True

    def on_depth_press(self, event):
        self.dragging = "depth"
        self.drag_last = [event.x, event.y]

    def on_drag(self, event):
        dx = event.x - self.drag_last[0]
        dy = event.y - self.drag_last[1]
        if self.dragging == "light":
            self.move_light_screen(dx, dy)
        elif self.dragging == "target":
            self.aim_at_mouse(event.x, event.y)
            self.dirty = True
        elif self.dragging == "depth":
            self.move_light_depth(-dy * 0.015)
        self.drag_last = [event.x, event.y]

    def on_release(self, _event):
        self.dragging = None
        self.drag_last = None

    def on_wheel(self, event):
        self.move_light_depth(0.22 if event.delta > 0 else -0.22)

    def aim_at_mouse(self, x, y):
        origin, direction = self.ray_from_mouse(x, y)
        hit = trace(origin, direction)
        if hit:
            self.target[:] = add(hit["point"], scale(hit["normal"], 0.04))
        else:
            self.target[:] = add(origin, scale(direction, 6.0))
        self.target[0] = clamp(self.target[0], -3.2, 3.2)
        self.target[1] = clamp(self.target[1], 0.12, 3.0)
        self.target[2] = clamp(self.target[2], -2.2, 5.0)
        self.dirty = True

    def ray_from_mouse(self, x, y):
        cam_pos, forward, right, up = camera_basis(self.camera_angle)
        aspect = W / H
        fov = math.radians(58)
        sx = (2.0 * (x / VIEW_W) - 1.0) * aspect * math.tan(fov / 2)
        sy = (1.0 - 2.0 * (y / VIEW_H)) * math.tan(fov / 2)
        direction = normalize(add(add(scale(right, sx), scale(up, sy)), forward))
        return cam_pos, direction

    def render(self):
        cam_pos, forward, right, up = camera_basis(self.camera_angle)
        rows = []
        aspect = W / H
        fov = math.radians(58)
        spot_dir = normalize(sub(self.target, self.light))

        for py in range(H):
            row = []
            sy = (1.0 - 2.0 * ((py + 0.5) / H)) * math.tan(fov / 2)
            for px in range(W):
                sx = (2.0 * ((px + 0.5) / W) - 1.0) * aspect * math.tan(fov / 2)
                ray_dir = normalize(add(add(scale(right, sx), scale(up, sy)), forward))
                hit = trace(cam_pos, ray_dir)
                if hit is None:
                    row.append("#050507")
                    continue
                row.append(to_hex(shade(hit, self.light, spot_dir)))
            rows.append("{" + " ".join(row) + "}")

        self.photo.put(" ".join(rows))
        self.draw_ui()

    def draw_ui(self):
        self.canvas.delete("ui")
        lx, ly = self.project_marker(self.light)
        tx, ty = self.project_marker(self.target)
        self.canvas.create_line(lx, ly, tx, ty, fill="#f4e6b8", dash=(5, 5), width=1, tags="ui")
        self.canvas.create_rectangle(lx - 15, ly - 15, lx + 15, ly + 15, fill="#ffffff", outline="#181818", width=2, tags="ui")
        self.canvas.create_oval(lx - 5, ly - 5, lx + 5, ly + 5, fill="#111111", outline="", tags="ui")
        self.canvas.create_rectangle(tx - 14, ty - 14, tx + 14, ty + 14, fill="#ffffff", outline="#181818", width=2, tags="ui")
        self.canvas.create_line(tx - 8, ty, tx + 8, ty, fill="#111111", width=2, tags="ui")
        self.canvas.create_line(tx, ty - 8, tx, ty + 8, fill="#111111", width=2, tags="ui")
        self.canvas.create_rectangle(0, VIEW_H - 38, VIEW_W, VIEW_H, fill="#000000", outline="", tags="ui")
        self.canvas.create_text(
            18,
            VIEW_H - 19,
            anchor="w",
            text="3D controls: drag square to move light, drag scene to aim at surfaces, right-drag or wheel changes depth, AD screen-move, WS depth, arrows height/camera.",
            fill="#e9dec9",
            font=("Segoe UI", 12),
            tags="ui",
        )

    def project_marker(self, point):
        cam_pos, forward, right, up = camera_basis(self.camera_angle)
        rel = sub(point, cam_pos)
        z = dot(rel, forward)
        if z <= 0.1:
            return VIEW_W / 2, VIEW_H / 2
        x = dot(rel, right) / z
        y = dot(rel, up) / z
        return VIEW_W / 2 + x * 700, VIEW_H / 2 - y * 700


def trace(origin, direction):
    closest = None
    for obj in SCENE:
        hit = obj.intersect(origin, direction)
        if hit and (closest is None or hit["t"] < closest["t"]):
            closest = hit
    return closest


def shade(hit, light, spot_dir):
    point = hit["point"]
    normal = hit["normal"]
    base = hit["color"]

    to_light = sub(light, point)
    light_distance = length(to_light)
    light_dir = normalize(to_light)
    facing = max(0.0, dot(normal, light_dir))

    cone = max(0.0, dot(scale(light_dir, -1), spot_dir))
    cone = smoothstep(0.72, 0.96, cone)
    falloff = 1.0 / (0.25 + light_distance * light_distance * 0.38)

    shadow = 1.0
    blocker = trace(add(point, scale(normal, EPS * 8)), light_dir)
    if blocker and blocker["t"] < light_distance - EPS:
        shadow = 0.16

    ambient = 0.12
    intensity = ambient + facing * cone * falloff * shadow * 4.2
    warm = (255, 213, 132)

    color = []
    for value, tint in zip(base, warm):
        lit = value * intensity + tint * max(0.0, intensity - 0.85) * 0.34
        color.append(int(clamp(lit, 0, 255)))

    return tuple(color)


class Plane:
    def __init__(self, point, normal, color, checker=False):
        self.point = point
        self.normal = normalize(normal)
        self.color = color
        self.checker = checker

    def intersect(self, origin, direction):
        denom = dot(self.normal, direction)
        if abs(denom) < EPS:
            return None
        t = dot(sub(self.point, origin), self.normal) / denom
        if t <= EPS:
            return None
        point = add(origin, scale(direction, t))
        color = self.color
        if self.checker:
            plank = int(math.floor(point[0] * 1.7) + math.floor(point[2] * 1.2)) & 1
            color = (57, 35, 25) if plank else (43, 28, 23)
        return {"t": t, "point": point, "normal": self.normal, "color": color}


class Sphere:
    def __init__(self, center, radius, color):
        self.center = center
        self.radius = radius
        self.color = color

    def intersect(self, origin, direction):
        oc = sub(origin, self.center)
        b = dot(oc, direction)
        c = dot(oc, oc) - self.radius * self.radius
        disc = b * b - c
        if disc < 0:
            return None
        root = math.sqrt(disc)
        t = -b - root
        if t <= EPS:
            t = -b + root
        if t <= EPS:
            return None
        point = add(origin, scale(direction, t))
        return {"t": t, "point": point, "normal": normalize(sub(point, self.center)), "color": self.color}


class Box:
    def __init__(self, min_corner, max_corner, color):
        self.min = min_corner
        self.max = max_corner
        self.color = color

    def intersect(self, origin, direction):
        tmin = -1e9
        tmax = 1e9
        normal = [0.0, 0.0, 0.0]
        for axis in range(3):
            if abs(direction[axis]) < EPS:
                if origin[axis] < self.min[axis] or origin[axis] > self.max[axis]:
                    return None
                continue
            inv = 1.0 / direction[axis]
            t1 = (self.min[axis] - origin[axis]) * inv
            t2 = (self.max[axis] - origin[axis]) * inv
            sign = -1.0 if t1 < t2 else 1.0
            if t1 > t2:
                t1, t2 = t2, t1
            if t1 > tmin:
                tmin = t1
                normal = [0.0, 0.0, 0.0]
                normal[axis] = sign
            tmax = min(tmax, t2)
            if tmin > tmax:
                return None
        if tmin <= EPS:
            return None
        point = add(origin, scale(direction, tmin))
        return {"t": tmin, "point": point, "normal": normal, "color": self.color}


def camera_basis(angle):
    radius = 6.0
    cam_pos = [math.sin(angle) * radius, 2.1, -4.3 + math.cos(angle) * 1.2]
    target = [0.0, 1.0, 2.6]
    forward = normalize(sub(target, cam_pos))
    right = normalize(cross(forward, [0.0, 1.0, 0.0]))
    up = normalize(cross(right, forward))
    return cam_pos, forward, right, up


def smoothstep(edge0, edge1, value):
    t = clamp((value - edge0) / (edge1 - edge0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def add(a, b):
    return [a[0] + b[0], a[1] + b[1], a[2] + b[2]]


def sub(a, b):
    return [a[0] - b[0], a[1] - b[1], a[2] - b[2]]


def scale(v, amount):
    return [v[0] * amount, v[1] * amount, v[2] * amount]


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def cross(a, b):
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]


def length(v):
    return math.sqrt(dot(v, v))


def normalize(v):
    size = length(v)
    if size < EPS:
        return [0.0, 0.0, 1.0]
    return [v[0] / size, v[1] / size, v[2] / size]


def clamp(value, low, high):
    return max(low, min(high, value))


def to_hex(rgb):
    return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"


SCENE = [
    Plane([0, 0, 0], [0, 1, 0], (48, 31, 24), checker=True),
    Plane([0, 0, 5.2], [0, 0, -1], (31, 25, 22)),
    Plane([-3.6, 0, 0], [1, 0, 0], (24, 21, 19)),
    Plane([3.6, 0, 0], [-1, 0, 0], (28, 23, 21)),
    Box([-0.85, 0.0, 2.15], [0.25, 1.2, 3.05], (76, 54, 40)),
    Box([1.15, 0.0, 1.15], [2.0, 0.95, 2.0], (58, 45, 37)),
    Box([-2.95, 0.0, 3.45], [-2.05, 1.05, 4.35], (43, 33, 29)),
    Box([-0.35, 1.25, 5.04], [0.8, 2.55, 5.12], (115, 86, 58)),
    Sphere([-1.55, 0.55, 1.6], 0.55, (92, 52, 43)),
]


if __name__ == "__main__":
    Ray3DLight().run()
