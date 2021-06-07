# Changelog

This package uses a variant of [Semantic Versioning](https://semver.org/) that
makes additional promises during the initial development (major version 0):
whenever breaking changes to the public API are published, the first non-zero
version number will increase. For example, code that uses version 0.6.0 if this
package will also work with version 0.6.1, but may break with version 0.7.0.

## Unreleased

No changes yet!

## v0.2.1

- ADD: {doc}`Installation guide <guide/install>`.
- FIX: Mark {mod}`~cernml.lsa_utils` as type-annotated.
- FIX: Include `pjlsa` dependency in extra `all`.

## v0.2.0

- BREAKING: rename {class}`~cernml.japc_utils.ParamStream` and {class}`~cernml.japc_utils.ParamGroupStream` methods: `wait_next()` becomes {meth}`~cernml.japc_utils.ParamStream.pop_or_wait()`, `next_if_ready()` becomes {meth}`~cernml.japc_utils.ParamStream.pop_if_ready()`.
- BREAKING: Refactor the renderer API: `SimpleRenderer` is replaced by {class}`~cernml.mpl_utils.FigureRenderer`, which is an {term}`ABC <abstract base class>`. Replace `from_generator()` with {meth}`~cernml.mpl_utils.FigureRenderer.from_callback()`. 
- ADD: Method {meth}`~cernml.japc_utils.ParamStream.wait_for_next()` to {class}`~cernml.japc_utils.ParamStream` and {class}`~cernml.japc_utils.ParamGroupStream`.
- ADD: {func}`~cernml.mpl_utils.make_renderer()` and {class}`~cernml.mpl_utils.RendererGroup`.
- ADD: {func}`~cernml.lsa_utils.get_cycle_type_attributes()` from cernml-coi-funcs 0.2.2.
- ADD: {attr}`Scaler.scaled_space <cernml.gym_utils.Scaler.scaled_space>`.
- ADD: The *symmetric* parameter to {class}`~cernml.gym_utils.Scaler`, {func}`~cernml.gym_utils.scale_from_box()` and {func}`~cernml.gym_utils.unscale_into_box()`.
- OTHER: Extend and reorganize the documentation.

## v0.1.0

Initial version. Code has been extracted from
[cernml-coi](https://gitlab.cern.ch/be-op-ml-optimization/cernml-coi/) and
[cernml-coi-funcs](https://gitlab.cern.ch/be-op-ml-optimization/cernml-coi-funcs/).
Documentation has been adjusted.
