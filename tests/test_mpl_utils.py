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
from unittest.mock import MagicMock, Mock, call

import matplotlib as mpl
import pytest

from cernml import coi
from cernml.mpl_utils import (
    FigureRenderer,
    FigureStrategy,
    HumanStrategy,
    InconsistentRenderModeError,
    MatplotlibFiguresStrategy,
    Renderer,
    RendererGroup,
    RenderGenerator,
    iter_matplotlib_figures,
    render_generator,
)

if t.TYPE_CHECKING:
    from matplotlib.figure import Figure

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


class TestIterMplFigures:
    def test_nothing(self) -> None:
        assert list(iter_matplotlib_figures()) == []

    def test_empty_list(self) -> None:
        assert list(iter_matplotlib_figures([])) == []

    def test_single_figure(self) -> None:
        fig = Mock(mpl.figure.Figure)
        assert list(iter_matplotlib_figures(fig)) == [("", fig)]

    def test_iterator(self) -> None:
        figs = [Mock(mpl.figure.Figure) for _ in range(3)]
        assert list(iter_matplotlib_figures(figs)) == [
            ("", figs[0]),
            ("", figs[1]),
            ("", figs[2]),
        ]

    def test_titles(self) -> None:
        figs = [Mock(mpl.figure.Figure) for _ in range(4)]
        inputs: list = [
            ["title 1", figs[0]],
            ("title 2", figs[1]),
            figs[2],
            (i for i in ["title 4", figs[3]]),
        ]
        assert list(iter_matplotlib_figures(inputs)) == [
            ("title 1", figs[0]),
            ("title 2", figs[1]),
            ("", figs[2]),
            ("title 4", figs[3]),
        ]

    def test_mapping(self) -> None:
        figs = [Mock(mpl.figure.Figure) for _ in range(3)]
        inputs: dict = {
            "title 1": figs[0],
            "title 2": figs[1],
            "": figs[2],
        }
        assert list(iter_matplotlib_figures(inputs)) == [
            ("title 1", figs[0]),
            ("title 2", figs[1]),
            ("", figs[2]),
        ]

    def test_multi_args(self) -> None:
        figs = [Mock(mpl.figure.Figure) for _ in range(10)]
        assert list(iter_matplotlib_figures(*figs)) == [("", fig) for fig in figs]

    def test_bad_string(self) -> None:
        with pytest.raises(TypeError, match="not a figure: 'string'"):
            iter_matplotlib_figures(t.cast(t.Any, "string"))

    def test_bad_string_list(self) -> None:
        with pytest.raises(TypeError, match="not a figure: 'string'"):
            iter_matplotlib_figures([t.cast(t.Any, "string")])

    def test_bad_mapping(self) -> None:
        class BadDict(dict):
            items = None  # type: ignore[assignment]

        figs = [Mock(mpl.figure.Figure) for _ in range(2)]
        inputs = BadDict({"title 1": figs[0], "title 2": figs[1]})
        with pytest.raises(TypeError, match="not a figure: 'title 1'"):
            iter_matplotlib_figures(inputs)

    def test_bad_tuple_length_1(self) -> None:
        with pytest.raises(ValueError, match="not enough values to unpack"):
            iter_matplotlib_figures([t.cast(t.Any, ("a",))])

    def test_bad_tuple_length_3(self) -> None:
        with pytest.raises(ValueError, match="too many values to unpack"):
            iter_matplotlib_figures([t.cast(t.Any, ("a", Mock(), Mock()))])

    def test_skip_instance_items(self) -> None:
        class WeirdDict(dict):
            pass

        figs = [Mock(mpl.figure.Figure) for _ in range(2)]
        inputs = WeirdDict({"title 1": figs[0], "title 2": figs[1]})
        inputs.items = None  # type: ignore[method-assign, assignment]
        assert list(iter_matplotlib_figures(inputs)) == [
            ("title 1", figs[0]),
            ("title 2", figs[1]),
        ]

    def test_accept_sequence_style_tuple(self) -> None:
        fig = Mock(mpl.figure.Figure)

        class WeirdTuple:
            def __getitem__(self, key: int) -> str | Figure:
                if key == 0:
                    return "title"
                if key == 1:
                    return fig
                raise IndexError(key)

        assert list(iter_matplotlib_figures([t.cast(t.Any, WeirdTuple())])) == [
            ("title", fig)
        ]


class TestInterface:
    def test_close_does_nothing(self) -> None:
        class NullRenderer(Renderer):
            def update(self) -> None:
                pass

        assert NullRenderer(None).close() is None  # type: ignore[func-returns-value]


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
            ("human", HumanStrategy),
            ("matplotlib_figures", MatplotlibFiguresStrategy),
            (None, type(None)),
        ],
    )
    def test_mode_selection(self, mode: str, strat_type: type) -> None:
        renderer = MockFigureRenderer(render_mode=mode)
        with closing(renderer):
            assert isinstance(renderer.strategy, strat_type)

    def test_update_logic(self) -> None:
        title = Mock()
        strategy = Mock(FigureStrategy)
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
        strategy = Mock(FigureStrategy)
        renderers = [
            Mock(Renderer, strategy=strategy, name=f"Renderer #{i}")
            for i in range(1, 6)
        ]
        group = RendererGroup(renderers)
        assert list(group) == renderers
        assert len(group) == len(renderers)
        assert isinstance(group, Renderer)
        assert isinstance(group, tuple)

    @pytest.mark.parametrize("mode", ["human", "matplotlib_figures"])
    def test_update_all(self, mode: str) -> None:
        strategy = Mock(FigureStrategy)
        group = RendererGroup(
            MagicMock(FigureRenderer, strategy=strategy, name=f"Renderer #{i}")
            for i in range(1, 6)
        )
        group.update()
        for renderer in group:
            t.cast(Mock, renderer.update).assert_called_once_with()

    @pytest.mark.parametrize("mode", ["human", "matplotlib_figures"])
    def test_close_all(self, mode: str) -> None:
        strategy = Mock(FigureStrategy)
        group = RendererGroup(
            MagicMock(FigureRenderer, strategy=strategy, name=f"Renderer #{i}")
            for i in range(1, 6)
        )
        group.close()
        for renderer in group:
            t.cast(Mock, renderer.close).assert_called_once_with()

    def test_update_empty_group(self) -> None:
        group = RendererGroup()
        assert group.update() is None

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
        with closing(stack), pytest.raises(InconsistentRenderModeError):
            RendererGroup(renderers)

    @pytest.mark.parametrize(
        "modes",
        [
            ("human", "matplotlib_figures"),
            ("matplotlib_figures", "human"),
        ],
    )
    def test_inconsistent_order_modify(self, modes: tuple[str, str]) -> None:
        renderers = RendererGroup(
            (
                MockFigureRenderer(render_mode=modes[0]),
                MockFigureRenderer(render_mode=modes[0]),
            )
        )
        renderers[1].strategy = Renderer.KNOWN_STRATEGIES[modes[1]]
        with closing(renderers), pytest.raises(InconsistentRenderModeError):
            renderers.update()

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

    def test_two_instances(self) -> None:
        callback = Mock(name="callback")

        class Container(coi.Problem):
            metadata: dict[str, t.Any] = {  # noqa: RUF012
                "render_modes": ["human", "matplotlib_figures"]
            }

            def __init__(self, name: str) -> None:
                self.name = name
                super().__init__(render_mode="matplotlib_figures")

            @render_generator
            def update(self, _: Figure) -> None:
                callback(self)

            def __repr__(self) -> str:  # pragma: no cover
                return f"{self.__class__.__name__}({self.name!r})"

        c1 = Container("c1")
        c2 = Container("c2")
        c1.update()
        c2.update()
        assert callback.call_args_list == [call(c1), call(c2)]

    def test_good_double_assign(self) -> None:
        class Container(coi.Problem):
            @render_generator
            def first(self, _: Figure) -> None:  # pragma: no cover
                pass

        Container.first.__set_name__(Container, "first")

    def test_bad_assign(self) -> None:
        class Container(coi.Problem):
            first: _RenderDescriptor

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
                def first(self, _: Figure) -> None:  # pragma: no cover
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
            def update(self, _: Figure) -> None:  # pragma: no cover
                pass

        container = Container()
        with pytest.raises(AttributeError, match="render_mode"):
            container.update()

    def test_delete_render_generator(self) -> None:
        class MyProblem(coi.Problem):
            metadata = {  # noqa: RUF012
                "render_modes": ["matplotlib_figures"],
            }

            def __init__(self, render_mode: str | None = None) -> None:
                super().__init__(render_mode)
                self.ncalls = 0

            @render_generator
            def update(self, _: Figure) -> RenderGenerator:
                self.ncalls = 0
                while True:
                    self.ncalls += 1
                    yield

        problem = MyProblem(render_mode="matplotlib_figures")
        assert problem.ncalls == 0
        # Ensure that the generator works.
        problem.update()
        assert problem.ncalls == 1
        problem.update()
        assert problem.ncalls == 2
        # Deleting the attribute should restart the generator.
        del problem.update
        problem.update()
        assert problem.ncalls == 1
        problem.update()
        assert problem.ncalls == 2

    def test_bad_delete(self) -> None:
        class MyProblem(coi.Problem):
            update: _RenderDescriptor[MyProblem]

        @render_generator
        def update(self: MyProblem, _: Figure) -> None:
            pass

        MyProblem.update = update

        problem = MyProblem()
        with pytest.raises(TypeError, match="without calling __set_name__"):
            del problem.update
