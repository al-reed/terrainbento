# coding: utf8
# !/usr/env/python

import numpy as np
from numpy.testing import assert_array_almost_equal  # assert_array_equal,

from terrainbento import BasicVs
from terrainbento.utilities import filecmp


def test_Aeff():
    U = 0.0001
    K = 0.001
    m = 1. / 3.
    n = 2. / 3.
    step = 1000
    hydraulic_conductivity = 0.1
    soil__initial_thickness = 0.1
    recharge_rate = 0.5
    node_spacing = 100.0

    # construct dictionary. note that D is turned off here
    params = {
        "model_grid": "RasterModelGrid",
        "clock": clock_simple,
        "number_of_node_rows": 3,
        "number_of_node_columns": 20,
        "node_spacing": 100.0,
        "north_boundary_closed": True,
        "south_boundary_closed": True,
        "regolith_transport_parameter": 0.,
        "water_erodability": K,
        "m_sp": m,
        "n_sp": n,
        "hydraulic_conductivity": hydraulic_conductivity,
        "soil__initial_thickness": soil__initial_thickness,
        "recharge_rate": recharge_rate,
        "random_seed": 3141,
        "BoundaryHandlers": "NotCoreNodeBaselevelHandler",
        "NotCoreNodeBaselevelHandler": {
            "modify_core_nodes": True,
            "lowering_rate": -U,
        },
    }

    model = BasicVs(params=params)
    for _ in range(200):
        model.run_one_step(step)

    # construct actual and predicted slopes
    actual_slopes = model.grid.at_node["topographic__steepest_slope"]
    actual_areas = model.grid.at_node["drainage_area"]

    alpha = (
        hydraulic_conductivity
        * soil__initial_thickness
        * node_spacing
        / recharge_rate
    )
    A_eff_predicted = actual_areas * np.exp(
        -(alpha * actual_slopes) / actual_areas
    )

    # assert aeff internally calculated correclty
    # assert_array_almost_equal(model.eff_area[model.grid.core_nodes],
    # A_eff_predicted[model.grid.core_nodes], decimal = 2)

    # assert correct s a relationship (slightly circular)
    predicted_slopes = (U / (K * (A_eff_predicted ** m))) ** (1. / n)
    assert_array_almost_equal(
        actual_slopes[model.grid.core_nodes],
        predicted_slopes[model.grid.core_nodes],
        decimal=3,
    )

    # assert all slopes above non effective
    predicted_slopes_normal = (U / (K * (actual_areas ** m))) ** (1. / n)
    assert np.all(
        actual_slopes[model.grid.core_nodes]
        > predicted_slopes_normal[model.grid.core_nodes]
    )


def test_steady_Ksp_no_precip_changer():
    U = 0.0001
    K = 0.001
    m = 1. / 3.
    n = 2. / 3.
    step = 1000

    # construct dictionary. note that D is turned off here
    params = {
        "model_grid": "RasterModelGrid",
        "clock": clock_simple,
        "number_of_node_rows": 3,
        "number_of_node_columns": 20,
        "node_spacing": 100.0,
        "north_boundary_closed": True,
        "south_boundary_closed": True,
        "regolith_transport_parameter": 0.,
        "water_erodability": K,
        "m_sp": m,
        "n_sp": n,
        "hydraulic_conductivity": 0.0,
        "soil__initial_thickness": 0.0,
        "recharge_rate": 0.5,
        "random_seed": 3141,
        "BoundaryHandlers": "NotCoreNodeBaselevelHandler",
        "NotCoreNodeBaselevelHandler": {
            "modify_core_nodes": True,
            "lowering_rate": -U,
        },
    }

    # construct and run model
    model = BasicVs(params=params)
    for _ in range(100):
        model.run_one_step(step)

    # construct actual and predicted slopes
    actual_slopes = model.grid.at_node["topographic__steepest_slope"]
    actual_areas = model.grid.at_node["drainage_area"]
    predicted_slopes = (U / (K * (actual_areas ** m))) ** (1. / n)

    # assert actual and predicted slopes are the same.
    assert_array_almost_equal(
        actual_slopes[model.grid.core_nodes[1:-1]],
        predicted_slopes[model.grid.core_nodes[1:-1]],
    )


def test_steady_Ksp_no_precip_changer_with_depression_finding():
    U = 0.0001
    K = 0.001
    m = 1. / 3.
    n = 2. / 3.
    step = 1000

    # construct dictionary. note that D is turned off here
    params = {
        "model_grid": "RasterModelGrid",
        "clock": clock_simple,
        "number_of_node_rows": 3,
        "number_of_node_columns": 20,
        "node_spacing": 100.0,
        "north_boundary_closed": True,
        "south_boundary_closed": True,
        "regolith_transport_parameter": 0.,
        "water_erodability": K,
        "m_sp": m,
        "n_sp": n,
        "hydraulic_conductivity": 0.0,
        "soil__initial_thickness": 0.0,
        "recharge_rate": 0.5,
        "random_seed": 3141,
        "depression_finder": "DepressionFinderAndRouter",
        "BoundaryHandlers": "NotCoreNodeBaselevelHandler",
        "NotCoreNodeBaselevelHandler": {
            "modify_core_nodes": True,
            "lowering_rate": -U,
        },
    }

    # construct and run model
    model = BasicVs(params=params)
    for _ in range(100):
        model.run_one_step(step)

    # construct actual and predicted slopes
    actual_slopes = model.grid.at_node["topographic__steepest_slope"]
    actual_areas = model.grid.at_node["drainage_area"]
    predicted_slopes = (U / (K * (actual_areas ** m))) ** (1. / n)

    # assert actual and predicted slopes are the same.
    assert_array_almost_equal(
        actual_slopes[model.grid.core_nodes[1:-1]],
        predicted_slopes[model.grid.core_nodes[1:-1]],
    )
