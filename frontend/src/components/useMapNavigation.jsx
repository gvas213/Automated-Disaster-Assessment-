import { useEffect } from 'react'

/**
@param {number}   currentIndex  - 0-based index from App.jsx
@param {Array}    maps          - full maps array from the API
@param {Object}   mapData       - { [map_id]: { bounds, geoData } }
@param {Function} setFlyTarget  - state setter for flyTarget in Map.jsx
 */

export function useMapNavigation(currentIndex, maps, mapData, setFlyTarget) {
  useEffect(() => {
    // Guard: nothing to do until data is loaded
    if (!maps.length) return

    const currentMap = maps[currentIndex]
    if (!currentMap) return

    const data = mapData[currentMap.map_id]
    if (!data?.bounds) return

    // avg the SW + NE corners to get the center of this tile
    const center = [
      (data.bounds[0][0] + data.bounds[1][0]) / 2,
      (data.bounds[0][1] + data.bounds[1][1]) / 2,
    ]

    setFlyTarget({ center, id: currentMap.map_id }) // triggers FlyToLocation
  }, [currentIndex, maps, mapData, setFlyTarget]) // re-runs on every arrow press
}