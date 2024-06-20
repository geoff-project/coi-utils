# SPDX-FileCopyrightText: 2020-2024 CERN
# SPDX-FileCopyrightText: 2023-2024 GSI Helmholtzzentrum für Schwerionenforschung
# SPDX-FileNotice: All rights not expressly granted are reserved.
#
# SPDX-License-Identifier: GPL-3.0-or-later OR EUPL-1.2+

"""Tests for `cernml.mpl_utils`."""

from __future__ import annotations

import sys
import typing as t
from contextlib import ExitStack, closing
from unittest.mock import MagicMock, Mock

import matplotlib as mpl
import pytest

from cernml import coi
from cernml.mpl_utils import (
    AbstractRenderer,
    FigureRenderer,
    Renderer,
    RendererGroup,
    _strategies,
    render_generator,
)

if t.TYPE_CHECKING:
    from cernml.mpl_utils._renderer import _RenderDescriptor


class MockFigureRenderer(FigureRenderer):
    def __init__(self, title: t.Any = None, *, render_mode: str | None) -> None:
        super().__init__(title, render_mode=render_mode)
        self._init_figure = Mock(name="bound method _init_figure")
        self._update_figure = Mock(name="bound method _update_figure")

    _init_figure = Mock(name="function _init_figure")
    _update_figure = Mock(name="function _update_figure")


@pytest.fixture(scope="module", autouse=True)
def _mpl_backend() -> t.Iterator[None]:
    old_backend = mpl.rcParams["backend"]
    mpl.use("agg")
    try:
        yield
    finally:
        mpl.use(old_backend)


def test_fixture() -> None:
    assert mpl.rcParams["backend"] == "agg"


class TestFigureRenderer:
    def test_requires_super_init(self) -> None:
        class BadRenderer(FigureRenderer):
            def __init__(self, *args: object) -> None:
                pass

            _init_figure = _update_figure = Mock()

        renderer = BadRenderer("human")
        with pytest.raises(TypeError, match=r"super\(\).__init__\(\) not called"):
            renderer.update()

    @pytest.mark.parametrize(
        ("mode", "strat_type"),
        [
            ("human", _strategies.HumanStrategy),
            ("matplotlib_figures", _strategies.MatplotlibFiguresStrategy),
            (None, type(None)),
        ],
    )
    def test_mode_selection(self, mode: str, strat_type: type) -> None:
        renderer = MockFigureRenderer(render_mode=mode)
        with closing(renderer):
            assert isinstance(renderer.strategy, strat_type)

    def test_update_logic(self) -> None:
        title = Mock()
        strategy = Mock(_strategies.FigureStrategy)
        renderer = MockFigureRenderer(title=title, render_mode=strategy)
        assert renderer.strategy is strategy
        assert renderer.figure is None

        res = renderer.update()
        strategy.make_figure.assert_called_once_with(title)
        strategy.update_figure.assert_called_once_with(renderer.figure)
        assert renderer.figure == strategy.make_figure.return_value
        assert res == strategy.update_figure.return_value
        renderer._init_figure.assert_called_once_with(renderer.figure)
        renderer._update_figure.assert_not_called()

        res = renderer.update()
        renderer._init_figure.assert_called_once_with(renderer.figure)
        renderer._update_figure.assert_called_once_with(renderer.figure)
        assert res == strategy.update_figure.return_value
        assert strategy.update_figure.call_count == 2

    def test_none_strategy(self) -> None:
        mock_figure = Mock()
        renderer = MockFigureRenderer(render_mode=None)
        assert renderer.strategy is None
        assert renderer.figure is None
        res = renderer.update()
        renderer._init_figure.assert_not_called()
        renderer._update_figure.assert_not_called()
        assert res is None
        assert renderer.strategy is None
        assert renderer.figure is None
        renderer.figure = mock_figure
        res = renderer.update()
        renderer._init_figure.assert_not_called()
        renderer._update_figure.assert_not_called()
        assert res is None
        assert renderer.strategy is None
        assert renderer.figure is mock_figure

    def test_human_extra_logic(self) -> None:
        figure = Mock()
        renderer = MockFigureRenderer(render_mode="human")
        renderer.figure = figure
        result = renderer.update()
        assert result is None
        figure.show.assert_called_once()
        figure.canvas.draw_idle.assert_called_once()

    @pytest.mark.parametrize("title", [None, Mock()])
    def test_mpl_figures_retval(self, title: t.Any) -> None:
        renderer = MockFigureRenderer(title, render_mode="matplotlib_figures")
        result = renderer.update()
        if title is None:
            assert result == (renderer.figure,)
        else:
            assert result == ((str(title), renderer.figure),)

    def test_close_closes_figure(self, monkeypatch: pytest.MonkeyPatch) -> None:
        pyplot = Mock()
        figure = Mock()
        monkeypatch.setattr("matplotlib.pyplot.close", pyplot.close)
        renderer = MockFigureRenderer(render_mode="human")
        renderer.figure = figure
        renderer.close()
        pyplot.close.assert_called_once_with(figure)

    def test_close_avoids_calling_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        pyplot = Mock()
        monkeypatch.setattr("matplotlib.pyplot.close", pyplot.close)
        renderer = MockFigureRenderer(render_mode="human")
        renderer.close()
        pyplot.close.assert_not_called()

    def test_unknown_render_mode(self) -> None:
        with pytest.raises(KeyError, match="numpy_array"):
            MockFigureRenderer(render_mode="numpy_array")


class TestRendererGroup:
    def test_is_tuple(self) -> None:
        renderers = [Mock(Renderer, name=f"Renderer #{i}") for i in range(1, 6)]
        group = RendererGroup(renderers)
        assert list(group) == renderers
        assert len(group) == len(renderers)
        assert not isinstance(group, Renderer)
        assert isinstance(group, AbstractRenderer)
        assert isinstance(group, tuple)

    @pytest.mark.parametrize("mode", ["human", "matplotlib_figures"])
    def test_update_all(self, mode: str) -> None:
        group = RendererGroup(
            MagicMock(FigureRenderer, name=f"Renderer #{i}") for i in range(1, 6)
        )
        group.update()
        for renderer in group:
            t.cast(Mock, renderer.update).assert_called_once_with()

    def test_update_empty_group(self) -> None:
        group = RendererGroup()
        assert group.update() == []

    @pytest.mark.parametrize(
        "modes",
        [
            ("human", "matplotlib_figures"),
            ("matplotlib_figures", "human"),
        ],
    )
    def test_inconsistent_order(self, modes: tuple[str, ...]) -> None:
        renderers = tuple(MockFigureRenderer(render_mode=mode) for mode in modes)
        stack = ExitStack()
        for renderer in renderers:
            stack.enter_context(closing(renderer))
        with stack, pytest.raises(RuntimeError):
            RendererGroup(renderers).update()

    def test_mpl_figure_retval(self) -> None:
        group = RendererGroup(
            [
                FigureRenderer.from_callback(
                    func=Mock(name=f"Renderer callback #{i}", return_value=None),
                    title=f"Renderer title #{i}",
                    render_mode="matplotlib_figures",
                )
                for i in range(1, 5)
            ]
        )
        result = group.update()
        assert result == [
            (f"Renderer title #{i+1}", t.cast(FigureRenderer, renderer).figure)
            for i, renderer in enumerate(group)
        ]


class TestRenderGenerator:
    # This test class merely covers weird edge cases that shouldn't be
    # enumerated in the doctest of mpl_utils.render_generator.

    def test_good_double_assign(self) -> None:
        class Container(coi.Problem):
            @render_generator
            def first(self, _: mpl.figure.Figure) -> None:  # pragma: no cover
                pass

        Container.first.__set_name__(Container, "first")

    def test_bad_assign(self) -> None:
        class Container(coi.Problem):
            first: _RenderDescriptor | None = None

        Container.first = render_generator(lambda _self, _fig: None)
        with pytest.raises(TypeError, match="__set_name__"):
            _ = Container().first

    def test_bad_double_assign(self) -> None:
        # On Python 3.12+, we receive the original exception; before, it
        # got wrapped in a RuntimeError. See
        # <https://github.com/python/cpython/issues/77757>.
        with pytest.raises((RuntimeError, TypeError)) as exc:

            class Container(coi.Problem):
                @render_generator
                def first(self, _: mpl.figure.Figure) -> None:  # pragma: no cover
                    pass

                second = first

        if sys.version_info < (3, 12):  # pragma: no cover
            assert isinstance(exc.value.__cause__, TypeError)
        else:  # pragma: no cover
            assert isinstance(exc.value, TypeError)

    def test_bad_class(self) -> None:
        class Container:
            render_mode: str | None
            metadata: dict[str, t.Any]
            spec: coi.registration.MinimalEnvSpec
            unwrapped: coi.protocols.Problem

            def close(self) -> None:
                raise NotImplementedError

            def render(self) -> t.Any:
                raise NotImplementedError

            def get_wrapper_attr(self, name: str) -> t.Any:
                raise NotImplementedError

            @render_generator
            def update(self, _: mpl.figure.Figure) -> None:  # pragma: no cover
                pass

        container = Container()
        with pytest.raises(AttributeError, match="render_mode"):
            container.update()
