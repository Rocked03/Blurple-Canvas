from __future__ import annotations


class Coordinates:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def to_tuple(self):
        return self.x, self.y

    def bbox_to(self, xy1: Coordinates):
        return BoundingBox(self, xy1)

    def __str__(self):
        return f"({self.x}, {self.y})"

    def __eq__(self, other):
        return (
            isinstance(other, Coordinates) and self.x == other.x and self.y == other.y
        )

    def __hash__(self):
        return hash((self.x, self.y))

    def __add__(self, other):
        if isinstance(other, Coordinates):
            return Coordinates(self.x + other.x, self.y + other.y)
        if isinstance(other, int):
            return Coordinates(self.x + other, self.y + other)
        if isinstance(other, tuple):
            return Coordinates(self.x + other[0], self.y + other[1])
        raise TypeError(f"Unsupported type: {type(other)}")

    def __sub__(self, other):
        if isinstance(other, Coordinates):
            return Coordinates(self.x - other.x, self.y - other.y)
        if isinstance(other, int):
            return Coordinates(self.x - other, self.y - other)
        if isinstance(other, tuple):
            return Coordinates(self.x - other[0], self.y - other[1])
        raise TypeError(f"Unsupported type: {type(other)}")


class BoundingBox:
    def __init__(self, xy0: Coordinates, xy1: Coordinates = Coordinates(0, 0)):
        self.x0, self.y0 = xy0.to_tuple()
        self.x1, self.y1 = xy1.to_tuple()

        if self.x0 > self.x1:
            self.x0, self.x1 = self.x1, self.x0
        if self.y0 > self.y1:
            self.y0, self.y1 = self.y1, self.y0

        self.xy0 = Coordinates(self.x0, self.y0)
        self.xy1 = Coordinates(self.x1, self.y1)

        self.width = self.xy1.x - self.xy0.x + 1
        self.height = self.xy1.y - self.xy0.y + 1

        self.size = (self.width, self.height)
        self.area = self.width * self.height

    @staticmethod
    def from_coordinates(x_0, y_0, x_1, y_1):
        return BoundingBox(Coordinates(x_0, y_0), Coordinates(x_1, y_1))

    def to_tuple(self):
        return self.x0, self.y0, self.x1, self.y1

    def __contains__(self, item):

        from objects.pixel import Pixel

        if isinstance(item, Coordinates):
            return self.x0 <= item.x <= self.x1 and self.y0 <= item.y <= self.y1
        elif isinstance(item, BoundingBox):
            return item.xy0 in self and item.xy1 in self
        elif isinstance(item, Pixel):
            return item.xy in self
        else:
            raise TypeError(f"Unsupported type: {type(item)}")

    def __str__(self):
        return f"{self.xy0} - {self.xy1}"

    def __eq__(self, other):
        return (
            isinstance(other, BoundingBox)
            and self.xy0 == other.xy0
            and self.xy1 == other.xy1
        )

    def __hash__(self):
        return hash((self.xy0, self.xy1))

    def __add__(self, other):
        if isinstance(other, BoundingBox):
            return BoundingBox(self.xy0 + other.xy0, self.xy1 + other.xy1)
        raise TypeError(f"Unsupported type: {type(other)}")
