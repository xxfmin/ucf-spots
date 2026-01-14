/**
 * Utility functions for handling accordion state
 */

/**
 * Updates the expanded items array when toggling an accordion item
 * ensures only one top-level building accordion can be open at a time
 * 
 * @param value The accordion item ID being toggled
 * @param prevItems The current array of expanded accordion items
 * @returns The updated array of expanded accordion items
 */
export const getUpdatedAccordionItems = (value: string, prevItems: string[]): string[] => {
  // If the item is already in the list, just remove it (close the accordion)
  if (prevItems.includes(value)) {
    return prevItems.filter((item) => item !== value);
  }

  // Handle only top-level facility accordions (ensure only one is open)
  // Match exactly building-{id} pattern (no additional segments)
  const buildingPattern = /^[^-]+$/; // Our IDs are just building names like 'BA1'

  if (buildingPattern.test(value)) {
    // For academic buildings, close any other open academic building
    const filteredItems = prevItems.filter(item => !buildingPattern.test(item));
    return [...filteredItems, value];
  }

  // For all other items, just add them
  return [...prevItems, value];
};
