#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
ClosedNodeBaselevelHandler handles modifying elevation for all closed nodes.
"""
import os
import numpy as np
from scipy.interpolate import interp1d

class ClosedNodeBaselevelHandler():
    """ Control the elevation of a single open boundary node.

    The `ClosedNodeBaselevelHandler` controls the elevation of all closed nodes
    on the model grid. The elevation change at these nodes is specified either
    as a constant or through a time or through a textfile that specifies the
    elevation change through time.

    Through the parameter `modify_closed_nodes` the user can determine if the
    closed nodes should be moved in the direction (up or down) specified by the
    elevation change directive, or if the non-closed nodes should be moved in
    the opposite direction.

    The `ClosedNodeBaselevelHandler` expects that `topographic__elevation` is a
    at-node model grid field. It will modify this field and `bedrock__elevation`
    if it exists.

    Methods
    -------
    run_one_step(dt)

    """

    def __init__(self,
                 grid,
                 modify_closed_nodes = False,
                 lowering_rate = None,
                 lowering_file_path = None,
                 model_end_elevation = None,
                 **kwargs):
        """
        Parameters
        ----------
        grid : landlab model grid
        modify_closed_nodes : boolean, optional
            Flag to indicate if the closed nodes or the non-closed nodes will
            be modified.
        lowering_rate : float, optional
            Lowering rate of the outlet node. One of `lowering_rate` and
            `lowering_file_path` is required. Units are implied by the
            model grids spatial scale and the time units of `dt`. Negative
            values mean that the outlet lowers.
        lowering_file_path : str, optional
            Lowering lowering history file path. One of `lowering_rate`
            and `lowering_file_path` is required. Units are implied by
            the model grids spatial scale and the time units of `dt`.
            This file should be readable with
            `np.loadtxt(filename, skiprows=1, delimiter=',')`
            Its first column is time and its second colum is the elevation
            change at the outlet since the onset of the model run. Negative
            values mean the outlet lowers.
        model_end_elevation : float, optional
            Average elevation of the nodes_to_lower at the end of the model run duration. When
            the outlet is lowered based on an lowering_file_path, a
            `model_end_elevation` can be set such that lowering is scaled
            based on the starting and ending outlet elevation. Default behavior
            is to not scale the lowering pattern.

        Examples
        --------
        Start by creating a landlab model grid and set its boundary conditions.

        >>> from landlab import RasterModelGrid
        >>> mg = RasterModelGrid(5, 5)
        >>> z = mg.add_zeros('node', 'topographic__elevation')
        >>> mg.set_closed_boundaries_at_grid_edges(bottom_is_closed=True,
        ...                                        left_is_closed=True,
        ...                                        right_is_closed=True,
        ...                                        top_is_closed=True)
        >>> mg.set_watershed_boundary_condition_outlet_id(
        ...     0, mg.at_node['topographic__elevation'], -9999.)
        >>> print(z.reshape(mg.shape))
        [[ 0.  0.  0.  0.  0.]
         [ 0.  0.  0.  0.  0.]
         [ 0.  0.  0.  0.  0.]
         [ 0.  0.  0.  0.  0.]
         [ 0.  0.  0.  0.  0.]]

        Now import the `ClosedNodeBaselevelHandler` and instantiate.

        >>> from terrainbento.boundary_condition_handlers import (
        ...                                         ClosedNodeBaselevelHandler)
        >>> bh = ClosedNodeBaselevelHandler(mg,
        ...                                 modify_closed_nodes = True,
        ...                                 lowering_rate = -0.1)
        >>> bh.run_one_step(10.0)

        We should expect that the boundary nodes (except for node 0) will all
        have lowered by -1.

        >>> print(z.reshape(mg.shape))
        [[-1. -1. -1. -1. -1.]
         [-1.  0.  0.  0. -1.]
         [-1.  0.  0.  0. -1.]
         [-1.  0.  0.  0. -1.]
         [-1. -1. -1. -1. -1.]]

        If we wanted instead for all of the non closed nodes to change their
        elevation, we would set `modify_closed_nodes = False`.

        >>> mg = RasterModelGrid(5, 5)
        >>> z = mg.add_zeros('node', 'topographic__elevation')
        >>> mg.set_closed_boundaries_at_grid_edges(bottom_is_closed=True,
        ...                                        left_is_closed=True,
        ...                                        right_is_closed=True,
        ...                                        top_is_closed=True)
        >>> mg.set_watershed_boundary_condition_outlet_id(
        ...     0, mg.at_node['topographic__elevation'], -9999.)
        >>> from terrainbento.boundary_condition_handlers import (
        ...                                         ClosedNodeBaselevelHandler)
        >>> bh = ClosedNodeBaselevelHandler(mg,
        ...                                 modify_closed_nodes = False,
        ...                                 lowering_rate = -0.1)
        >>> bh.run_one_step(10.0)
        >>> print(z.reshape(mg.shape))
        [[ 0.  0.  0.  0.  0.]
         [ 0.  1.  1.  1.  0.]
         [ 0.  1.  1.  1.  0.]
         [ 0.  1.  1.  1.  0.]
         [ 0.  0.  0.  0.  0.]]

        More complex baselevel histories can be provided with a
        `lowering_file_path`.

        """
        self.model_time = 0.0
        self.grid = grid
        self.modify_closed_nodes = modify_closed_nodes
        self.z = self.grid.at_node['topographic__elevation']

        # determine which nodes to lower
        if self.modify_closed_nodes:
            self.nodes_to_lower = self.grid.status_at_node != 0
            self.prefactor = 1.0
        else:
            self.nodes_to_lower = self.grid.status_at_node == 0
            self.prefactor = -1.0

        if (lowering_file_path is None) and (lowering_rate is None):
            raise ValueError(('ClosedNodeBaselevelHandler requires one of '
                              'lowering_rate and lowering_file_path'))
        else:
            if (lowering_rate is None):
                # initialize outlet elevation object
                if os.path.exists(lowering_file_path):

                    elev_change_df = np.loadtxt(lowering_file_path, skiprows=1, delimiter =',')
                    time = elev_change_df[:, 0]
                    elev_change = elev_change_df[:, 1]

                    if model_end_elevation is None:
                        scaling_factor = 1.0
                    else:
                        model_start_elevation = np.mean(self.z[self.nodes_to_lower])
                        scaling_factor = np.abs(model_start_elevation-model_end_elevation)/np.abs(elev_change[0]-elev_change[-1])
                    outlet_elevation = (scaling_factor*elev_change_df[:, 1]) + model_start_elevation
                    self.outlet_elevation_obj = interp1d(time, outlet_elevation)
                    self.lowering_rate = None
                else:
                    raise ValueError(('The lowering_file_path provided '
                                      'to ClosedNodeBaselevelHandler does not '
                                      'exist.'))
            elif (lowering_file_path is None):
                self.lowering_rate = lowering_rate
                self.outlet_elevation_obj = None
            else:
                raise ValueError(('Both an lowering_rate and a '
                                  'lowering_file_path have been provided '
                                  'to ClosedNodeBaselevelHandler. Please provide '
                                  'only one.'))

    def run_one_step(self, dt):
        """
        Run `ClosedNodeBaselevelHandler` forward and update node elevations.

        Parameters
        ----------
        dt : float
            Duration of model time to advance forward.
        """
        # increment model time
        self.model_time += dt

        # next, lower the correct nodes the desired amount
        # first, if we do not have an outlet elevation object
        if self.outlet_elevation_obj is None:

            # calculate lowering amount and subtract
            self.z[nodes_to_lower] += self.prefactor * self.lowering_rate * dt

            # if bedrock__elevation exists as a field, lower it also
            if 'bedrock__elevation' in self.grid.at_node:
                self.grid.at_node['bedrock__elevation'][self.nodes_to_lower] += self.prefactor * self.lowering_rate * dt

        # if there is an outlet elevation object
        else:
            # if bedrock__elevation exists as a field, lower it also
            # calcuate the topographic change required to match the current time's value for
            # outlet elevation. This must be done in case bedrock elevation exists, and must
            # be done before the topography is lowered
            topo_change = (self.prefactor * (self.z[self.nodes_to_lower]
                                - self.outlet_elevation_obj(self.model_time)))

            if 'bedrock__elevation' in self.grid.at_node:
                self.grid.at_node['bedrock__elevation'][self.nodes_to_lower] -= topo_change

            # lower topography
            self.z[self.nodes_to_lower] -= topo_change
