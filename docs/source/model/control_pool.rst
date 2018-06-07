==========================
Transparent Demand Control
==========================

.. graphviz::

    digraph graphname {
        graph [rankdir=LR, splines=lines, bgcolor="transparent"]
        controller [label=Controller]
        poola [label=Pool]
        controller -> poola
    }
