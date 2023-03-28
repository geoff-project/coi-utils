#!/usr/bin/env python
"""Tests for :mod:`cernml.mpl_utils`."""

# pylint: disable = missing-function-docstring
# pylint: disable = missing-class-docstring
# pylint: disable = import-outside-toplevel
# pylint: disable = redefined-outer-name

import typing as t
from unittest.mock import MagicMock, Mock

import matplotlib as mpl
import pytest

from cernml.mpl_utils import FigureRenderer, Renderer, RendererGroup, render_generator


@pytest.fixture(scope="module")
def mpl_backend() -> t.Iterator[None]:
    old_backend = mpl.rcParams["backend"]
    mpl.use("agg")
    try:
        yield
    finally:
        mpl.use(old_backend)


@pytest.mark.usefixtures("mpl_backend")
def test_fixture() -> None:
    assert mpl.rcParams["backend"] == "agg"


@pytest.mark.usefixtures("mpl_backend")
class TestFigureRenderer:
    class MockFigureRenderer(FigureRenderer):
        def __init__(self, title: t.Any = None) -> None:
            super().__init__(title)
            self._init_figure = Mock(name="bound method _init_figure")
            self._update_figure = Mock(name="bound method _update_figure")

        _init_figure = Mock(name="function _init_figure")
        _update_figure = Mock(name="function _update_figure")

    def test_requires_super_init(self) -> None:
        class BadRenderer(FigureRenderer):
            def __init__(self) -> None:
                # pylint: disable = super-init-not-called
                pass

            _init_figure = _update_figure = Mock()

        renderer = BadRenderer()
        with pytest.raises(TypeError, match=r"super\(\).__init__\(\) not called"):
            renderer.update("human")

    @pytest.mark.parametrize("mode", ["human", "matplotlib_figures"])
    def test_update_logic(self, mode: str) -> None:
        # pylint: disable = protected-access
        renderer = self.MockFigureRenderer()
        renderer.make_figure = Mock()  # type: ignore
        assert renderer.figure is None
        renderer.update(mode)
        assert renderer.figure == renderer.make_figure.return_value
        renderer._update_figure.assert_not_called()
        renderer.update(mode)
        renderer.make_figure.assert_called_once_with(mode)
        renderer._init_figure.assert_called_once_with(renderer.figure)
        renderer._update_figure.assert_called_with(renderer.figure)

    def test_human_extra_logic(self) -> None:
        figure = Mock()
        renderer = self.MockFigureRenderer()
        renderer.figure = figure
        result = renderer.update("human")
        assert result is None
        figure.show.assert_called_once()
        figure.canvas.draw_idle.assert_called_once()

    @pytest.mark.parametrize("title", [None, Mock()])
    def test_mpl_figures_retval(self, title: t.Any) -> None:
        renderer = self.MockFigureRenderer(title)
        result = renderer.update("matplotlib_figures")
        if title is None:
            assert result == (renderer.figure,)
        else:
            assert result == ((title, renderer.figure),)

    def test_close_closes_figure(self, monkeypatch: pytest.MonkeyPatch) -> None:
        pyplot = Mock()
        figure = Mock()
        monkeypatch.setattr("matplotlib.pyplot.close", pyplot.close)
        renderer = self.MockFigureRenderer()
        renderer.figure = figure
        renderer.close()
        pyplot.close.assert_called_once_with(figure)

    def test_close_avoids_calling_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        pyplot = Mock()
        monkeypatch.setattr("matplotlib.pyplot.close", pyplot.close)
        renderer = self.MockFigureRenderer()
        renderer.close()
        pyplot.close.assert_not_called()

    def test_unknown_render_mode(self) -> None:
        renderer = self.MockFigureRenderer()
        renderer.figure = Mock()
        with pytest.raises(KeyError, match="numpy_array"):
            renderer.update("numpy_array")


@pytest.mark.usefixtures("mpl_backend")
class TestRendererGroup:
    def test_is_tuple(self) -> None:
        renderers = [Mock(name=f"Renderer #{i+1}") for i in range(5)]
        group = RendererGroup(renderers)
        assert list(group) == renderers
        assert len(group) == len(renderers)
        assert isinstance(group, Renderer)
        assert isinstance(group, tuple)

    @pytest.mark.parametrize("mode", ["human", "matplotlib_figures", "unknown"])
    def test_update_all(self, mode: str) -> None:
        group = RendererGroup(
            MagicMock(FigureRenderer, name=f"Renderer #{i+1}") for i in range(5)
        )
        if mode == "unknown":
            with pytest.raises(KeyError, match=mode):
                group.update(mode)
            return
        group.update(mode)
        for renderer in group:
            t.cast(Mock, renderer.update).assert_called_once_with(mode)

    def test_mpl_figure_retval(self) -> None:
        group = RendererGroup(
            [
                FigureRenderer.from_callback(
                    func=Mock(name=f"Renderer callback #{i+1}", return_value=None),
                    title=f"Renderer title #{i+1}",
                )
                for i in range(4)
            ]
        )
        result = group.update("matplotlib_figures")
        assert result == [
            (f"Renderer title #{i+1}", t.cast(FigureRenderer, renderer).figure)
            for i, renderer in enumerate(group)
        ]


@pytest.mark.usefixtures("mpl_backend")
class TestRenderGenerator:
    # pylint: disable = too-few-public-methods

    # This test class merely covers weird edge cases that shouldn't be
    # enumerated in the doctest of mpl_utils.render_generator.

    def test_good_double_asign(self) -> None:
        class Container:
            @render_generator
            def first(self, _: mpl.figure.Figure) -> None:
                pass

        Container.first.__set_name__(Container, "first")  # pylint: disable=no-member

    def test_bad_asign(self) -> None:
        class Container:
            first: t.Optional[render_generator] = None

        Container.first = render_generator(lambda _self, _fig: None)
        with pytest.raises(TypeError, match="__set_name__"):
            _ = Container().first

    def test_bad_double_asign(self) -> None:
        with pytest.raises(RuntimeError) as exc:

            class Container:
                # pylint: disable = unused-variable
                @render_generator
                def first(self, _: mpl.figure.Figure) -> None:
                    pass

                second = first

        assert isinstance(exc.value.__cause__, TypeError)
