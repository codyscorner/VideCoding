from PyQt6.QtGui import QUndoCommand


class AddItemCommand(QUndoCommand):
    def __init__(self, scene, item, label="Add Item"):
        super().__init__(label)
        self.scene = scene
        self.item  = item

    def redo(self):  self.scene.addItem(self.item)
    def undo(self):  self.scene.removeItem(self.item)


class MoveNodeCommand(QUndoCommand):
    def __init__(self, node, old_pos, new_pos):
        super().__init__("Move Node")
        self.node    = node
        self.old_pos = old_pos
        self.new_pos = new_pos

    def redo(self):  self.node.setPos(self.new_pos)
    def undo(self):  self.node.setPos(self.old_pos)


class DeleteItemsCommand(QUndoCommand):
    def __init__(self, scene, nodes, connections, draw_items):
        super().__init__("Delete")
        self.scene       = scene
        self.nodes       = nodes
        self.connections = connections
        self.draw_items  = draw_items

    def redo(self):
        for c in self.connections:
            if c.scene() is self.scene: self.scene.removeItem(c)
        for n in self.nodes:
            if n.scene() is self.scene: self.scene.removeItem(n)
        for d in self.draw_items:
            if d.scene() is self.scene: self.scene.removeItem(d)

    def undo(self):
        for n in self.nodes:
            if n.scene() is None: self.scene.addItem(n)
        for c in self.connections:
            if c.scene() is None: self.scene.addItem(c)
            c.update_path()
        for d in self.draw_items:
            if d.scene() is None: self.scene.addItem(d)
