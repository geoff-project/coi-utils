# API Reference

## PyJapc Utilities

```{eval-rst}
.. automodule:: cernml.japc_utils

    .. autofunction:: subscriptions
    .. autofunction:: monitoring
    .. autofunction:: subscribe_stream
    .. autoclass:: ParamStream
        :members:
        :inherited-members:
        :exclude-members: Self
    .. autoclass:: ParamGroupStream
        :members:
        :inherited-members:
        :exclude-members: Self
    .. autoclass:: Header
        :show-inheritance:
        :members:
        :undoc-members:
    .. autoexception:: JavaException
    .. autoexception:: StreamError
```

## PJLSA Utilities

```{eval-rst}
.. automodule:: cernml.lsa_utils

    .. autofunction:: get_context_by_user
    .. autofunction:: get_settings_function
    .. autofunction:: incorporate_and_trim
    .. autoclass:: Incorporator
        :members:
    .. autoexception:: NotFound
```

## Gym Utilities

```{eval-rst}
.. automodule:: cernml.gym_utils

    .. autofunction:: scale_from_box
    .. autofunction:: unscale_into_box
    .. autoclass:: Scaler
        :members:
```

## Matplotlib Utilities

```{eval-rst}
.. automodule:: cernml.mpl_utils

    .. autofunction:: iter_matplotlib_figures
    .. autofunction:: make_renderer
    .. autoclass:: MatplotlibFigures
    .. autoclass:: MaybeTitledFigure
    .. autoclass:: RenderCallback
    .. autoclass:: RenderGenerator
    .. autoclass:: Renderer
        :show-inheritance:
        :members:
    .. autoclass:: FigureRenderer
        :show-inheritance:
        :members: from_callback, _init_figure, _update_figure
    .. autoclass:: RendererGroup
        :show-inheritance: tuple
    .. autodecorator:: render_generator
```
