# Isometric Animation Rules 

This is the breakdown of the pixel-level logic for a 4-frame South-facing walk cycle.
1. The "Locked Foot" Principle
In a walk cycle, one foot is always "planted" while the other moves. To prevent sliding, the planted foot must remain on the exact same world-space pixel while the character's root (center) moves forward.
If your character moves at a constant velocity v where:

Then over a 4-frame cycle, the character moves a total of 8 pixels horizontally and 4 pixels vertically. Your animation frames must account for this 8x4 displacement.
2. The 4-Frame Contact Logic (South-Facing)
For a South-facing walk (moving Down-Left in 2:1 isometric space), the "planted" foot must shift Up-Right within the sprite canvas to counteract the engine's downward movement.
| Frame | Phase | Body Logic (Y-Axis) | Foot Logic (Planted) |
|---|---|---|---|
| 1 | Contact (L) | Drop 1px: The leading foot strikes. The body "crunches" slightly from the impact. | Left foot is at the lead anchor point. Right foot is lifting off. |
| 2 | Passing (L) | Rise 1px: Body returns to neutral height as the weight moves over the Left foot. | Left foot locks: Move the left foot pixels +2x, -1y relative to Frame 1. |
| 3 | Contact (R) | Drop 1px: The right foot strikes the ground ahead. | Right foot is at the lead anchor point. Left foot is lifting. |
| 4 | Passing (R) | Rise 1px: Body returns to neutral height as weight moves over the Right foot. | Right foot locks: Move the right foot pixels +2x, -1y relative to Frame 3. |
3. Visualizing the "Bounce"
The 1-pixel vertical drop during the Contact frames (1 and 3) is essential. Without it, the character looks like a rigid sliding statue.
 * The Compression: When the heel hits (Contact), move the entire "Base Body" and "Gear" layers down by 1 pixel.
 * The Stretch: During the "Passing" frames (2 and 4), move them back up. This creates the "bob" that signals biological weight.
4. Grid Alignment Check
To ensure the feet land on the center of your 2:1 tiles:
 * Anchor Point: Define a specific pixel in your 48x48 canvas (e.g., 24, 40) as the "Center."
 * Strike Distance: In Frame 1, the lead foot should land exactly 4 pixels "ahead" (along the isometric axis) of the center.
 * The Hand-off: By Frame 3, that foot should have moved to 4 pixels "behind" the center as the other foot strikes 4 pixels "ahead."
> Pro-Tip: If you find that 8 pixels of movement per cycle is too fast for your gameplay vibe, you can halve the movement speed to \Delta x = 1, \Delta y = 0.5 (moving 1 pixel every two frames). This will make the walk feel more deliberate and "tactical."
> 
Technical Checklist for Aseprite
 * [ ] Frame 1 & 3: Entire character (excluding shadow) lowered by 1px.
 * [ ] Shadow: Remains static at the 48x48 base; does not "bounce" with the body.
 * [ ] Planted Foot: In Frame 2, the Left foot must be exactly +2x, -1y from its position in Frame 1.
 * [ ] Silhouette: Does the "Passing" frame create a clear gap between the legs? (Crucial for readability).
