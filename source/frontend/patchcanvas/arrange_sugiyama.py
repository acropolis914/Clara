#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2011-2024 Filipe Coelho <falktx@falktx.com>
# SPDX-License-Identifier: GPL-2.0-or-later

"""Sugiyama-style layered arrange plugin.

Classic hierarchical layout: break cycles, assign nodes to layers (longest path),
reduce crossings with barycenter sweeps down/up the layers, then place nodes into
columns with even vertical spacing. Registered as the ``sugiyama`` arrange
algorithm; self-contained apart from the shared ``_nodeGraph`` helper.
"""

from .arrangealgos import LayoutAlgorithm


class SugiyamaLayoutAlgorithm(LayoutAlgorithm):
    name = "sugiyama"
    label = "Sugiyama (layered)"

    node_gap = 64
    vertical_gap = 40
    sweeps = 8

    def arrange(self, nodes):
        from . import options
        from . import patchcanvas as _pc

        if len(nodes) < 2:
            return

        edges, incoming, group_name = _pc._nodeGraph(nodes)

        # 1. break cycles (DFS back-edges are dropped from the layering DAG)
        state = {n: 0 for n in nodes}
        dag_edges = {n: set() for n in nodes}

        def dfs(u):
            state[u] = 1
            for v in sorted(edges[u], key=lambda n: group_name.get(n, "")):
                if state[v] == 1:
                    continue
                dag_edges[u].add(v)
                if state[v] == 0:
                    dfs(v)
            state[u] = 2

        for n in nodes:
            if state[n] == 0:
                dfs(n)

        dag_incoming = {n: set() for n in nodes}
        for u in nodes:
            for v in dag_edges[u]:
                dag_incoming[v].add(u)

        # 2. longest-path layering
        layer = {n: 0 for n in nodes}
        for _ in range(len(nodes)):
            changed = False
            for u in nodes:
                for v in dag_edges[u]:
                    if layer[v] < layer[u] + 1:
                        layer[v] = layer[u] + 1
                        changed = True
            if not changed:
                break

        layers = {}
        for n in nodes:
            layers.setdefault(layer[n], []).append(n)
        sorted_layers = sorted(layers.keys())

        # 3. barycenter crossing reduction (down and up sweeps)
        for lyr in sorted_layers:
            layers[lyr].sort(key=lambda n: group_name.get(n, ""))
        index = {n: i for lyr in sorted_layers for i, n in enumerate(layers[lyr])}

        for s in range(self.sweeps):
            order = sorted_layers if s % 2 == 0 else list(reversed(sorted_layers))
            for lyr in order:
                col = layers[lyr]
                neighbours = dag_edges if s % 2 == 0 else dag_incoming
                def _bary(n):
                    rel = [index[m] for m in neighbours[n] if m in index]
                    return sum(rel) / float(len(rel)) if rel else float(index[n])
                col.sort(key=_bary)
                for i, n in enumerate(col):
                    index[n] = i

        # 4. coordinates: columns by width, nodes stacked with even gaps
        origin_x = min(n.x() for n in nodes)
        center_y = sum(n.y() + n.boundingRect().height() / 2.0 for n in nodes) / float(len(nodes))

        col_widths = {lyr: max(n.boundingRect().width() for n in layers[lyr])
                      for lyr in sorted_layers}
        col_x = {}
        curr_x = origin_x
        for lyr in sorted_layers:
            col_x[lyr] = curr_x
            curr_x += col_widths[lyr] + self.node_gap

        for lyr in sorted_layers:
            col = layers[lyr]
            total_h = (sum(n.boundingRect().height() for n in col)
                       + (len(col) - 1) * self.vertical_gap)
            cy = center_y - total_h / 2.0
            for n in col:
                n.setPos(col_x[lyr], cy)
                cy += n.boundingRect().height() + self.vertical_gap

        if getattr(options, "snap_enabled", True):
            gs = max(1, getattr(options, "grid_size", 20))
            for n in nodes:
                n.setPos(round(n.x() / gs) * gs, round(n.y() / gs) * gs)

        _pc.syncNodePositions(nodes)
