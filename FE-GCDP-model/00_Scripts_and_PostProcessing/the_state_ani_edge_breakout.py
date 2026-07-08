# state file generated using paraview version 6.0.1
import paraview
paraview.compatibility.major = 6
paraview.compatibility.minor = 0

#### import the simple module from the paraview
from paraview.simple import *
#### disable automatic camera reset on 'Show'
paraview.simple._DisableFirstRenderCameraReset()

# ----------------------------------------------------------------
# setup views used in the visualization
# ----------------------------------------------------------------

# Create a new 'Light'
light1 = CreateLight()
light1.Set(
    Intensity=0.6,
    Type='Positional',
    Position=[1653.6507052316917, 857.6787878670918, 451.023798492128],
    FocalPoint=[-267.80594280764484, -184.66440998475272, -291.09458282342905],
    ConeAngle=35.1,
)

# get the material library
materialLibrary1 = GetMaterialLibrary()

# create light
# Create a new 'Render View'
renderView1 = CreateView('RenderView')
renderView1.Set(
    ViewSize=[2566, 998],
    AxesGrid='Grid Axes 3D Actor',
    CenterOfRotation=[52.56469917297363, -114.94221353530884, 0.0],
    StereoType='Crystal Eyes',
    CameraPosition=[579.5320000000002, 355.847, 314.60500000000013],
    CameraFocalPoint=[160.0, 0.0, 0.0],
    CameraFocalDisk=1.0,
    CameraParallelScale=1.0,
    LegendGrid='Legend Grid Actor',
    PolarGrid='Polar Grid Actor',
    BackEnd='OSPRay raycaster',
    AdditionalLights=light1,
    OSPRayMaterialLibrary=materialLibrary1,
)

SetActiveView(None)

# ----------------------------------------------------------------
# setup view layouts
# ----------------------------------------------------------------

# create new layout object 'Layout #1'
layout1 = CreateLayout(name='Layout #1')
layout1.AssignView(0, renderView1)
layout1.SetSize(2566, 998)

# ----------------------------------------------------------------
# restore active view
SetActiveView(renderView1)
# ----------------------------------------------------------------

# ----------------------------------------------------------------
# setup the data processing pipelines
# ----------------------------------------------------------------

# create a new 'EnSight Reader'
a77d766177c585bcc5a218dbb61737d5955eecase = EnSightReader(registrationName='a77d766177c585bcc5a218dbb61737d5955ee..case', CaseFileName='/home/matthias/constitutive_modeling/Bonded-Anchor-pryout/FE-GCDP-model/Bonded_anchor_edge_breakout_test_SS-160/a77d766177c585bcc5a218dbb61737d5955ee947.case')
a77d766177c585bcc5a218dbb61737d5955eecase.Set(
    CellArrays=['alphaP', 'alphaD', 'damage', 'I1p'],
    PointArrays=['nodeDisplacements', 'nodeReactionForces', 'nonlocalDamage'],
)

# create a new 'Extract Block'
extractBlock1 = ExtractBlock(registrationName='ExtractBlock1', Input=a77d766177c585bcc5a218dbb61737d5955eecase)
extractBlock1.Set(
    Assembly='Hierarchy',
    Selectors=['/Root/ASSEMBLY_CONCRETE1_CONCRETE', '/Root/ASSEMBLY_STEEL1_MORTAR', '/Root/ASSEMBLY_STEEL1_STEEL'],
)

# create a new 'Reflect'
reflect1 = Reflect(registrationName='Reflect1', Input=extractBlock1)
reflect1.Set(
    Plane='Z Max',
    CopyInput=0,
)

# create a new 'Warp By Vector'
warpByVector2 = WarpByVector(registrationName='WarpByVector2', Input=reflect1)
warpByVector2.Vectors = ['POINTS', 'nodeDisplacements']

# create a new 'Threshold'
threshold1 = Threshold(registrationName='Threshold1', Input=warpByVector2)
threshold1.Set(
    Scalars=['CELLS', 'alphaD'],
    LowerThreshold=0.05,
    UpperThreshold=10000000000.0,
)

# create a new 'Warp By Vector'
warpByVector1 = WarpByVector(registrationName='WarpByVector1', Input=extractBlock1)
warpByVector1.Vectors = ['POINTS', 'nodeDisplacements']

# create a new 'Temporal Interpolator'
temporalInterpolator1 = TemporalInterpolator(registrationName='TemporalInterpolator1', Input=warpByVector1)
temporalInterpolator1.DiscreteTimeStepInterval = 0.01

# create a new 'Generate Time Steps'
generateTimeSteps1 = GenerateTimeSteps(registrationName='GenerateTimeSteps1', Input=temporalInterpolator1)
# generateTimeSteps1.TimeStepValues = [1.0, 1.0101010101010102, 1.02020202020202, 1.0303030303030303, 1.0404040404040404, 1.0505050505050506, 1.0606060606060606, 1.0707070707070707, 1.0808080808080809, 1.0909090909090908, 1.101010101010101, 1.1111111111111112, 1.121212121212121, 1.1313131313131313, 1.1414141414141414, 1.1515151515151516, 1.1616161616161615, 1.1717171717171717, 1.1818181818181819, 1.191919191919192, 1.202020202020202, 1.2121212121212122, 1.2222222222222223, 1.2323232323232323, 1.2424242424242424, 1.2525252525252526, 1.2626262626262625, 1.2727272727272727, 1.2828282828282829, 1.2929292929292928, 1.303030303030303, 1.3131313131313131, 1.3232323232323233, 1.3333333333333335, 1.3434343434343434, 1.3535353535353536, 1.3636363636363638, 1.3737373737373737, 1.3838383838383839, 1.393939393939394, 1.404040404040404, 1.4141414141414141, 1.4242424242424243, 1.4343434343434343, 1.4444444444444444, 1.4545454545454546, 1.4646464646464648, 1.474747474747475, 1.4848484848484849, 1.494949494949495, 1.5050505050505052, 1.5151515151515151, 1.5252525252525253, 1.5353535353535355, 1.5454545454545454, 1.5555555555555556, 1.5656565656565657, 1.5757575757575757, 1.5858585858585859, 1.595959595959596, 1.606060606060606, 1.6161616161616164, 1.6262626262626263, 1.6363636363636365, 1.6464646464646466, 1.6565656565656566, 1.6666666666666667, 1.676767676767677, 1.6868686868686869, 1.696969696969697, 1.7070707070707072, 1.7171717171717171, 1.7272727272727273, 1.7373737373737375, 1.7474747474747474, 1.7575757575757578, 1.7676767676767677, 1.7777777777777777, 1.787878787878788, 1.797979797979798, 1.8080808080808082, 1.8181818181818183, 1.8282828282828283, 1.8383838383838385, 1.8484848484848486, 1.8585858585858586, 1.8686868686868687, 1.878787878787879, 1.8888888888888888, 1.8989898989898992, 1.9090909090909092, 1.9191919191919191, 1.9292929292929295, 1.9393939393939394, 1.9494949494949496, 1.9595959595959598, 1.9696969696969697, 1.97979797979798, 1.98989898989899, 2.0]

import numpy as np
generateTimeSteps1.TimeStepValues = [1.0 + 1.0 - np.cos( i * np.pi / 100.0 ) for i in range(100) ]

# ----------------------------------------------------------------
# setup the visualization in view 'renderView1'
# ----------------------------------------------------------------

# show data from a77d766177c585bcc5a218dbb61737d5955eecase
a77d766177c585bcc5a218dbb61737d5955eecaseDisplay = Show(a77d766177c585bcc5a218dbb61737d5955eecase, renderView1, 'UnstructuredGridRepresentation')

# get 2D transfer function for 'vtkBlockColors'
vtkBlockColorsTF2D = GetTransferFunction2D('vtkBlockColors')

# get color transfer function/color map for 'vtkBlockColors'
vtkBlockColorsLUT = GetColorTransferFunction('vtkBlockColors')
vtkBlockColorsLUT.Set(
    InterpretValuesAsCategories=1,
    AnnotationsInitialized=1,
    TransferFunction2D=vtkBlockColorsTF2D,
    Annotations=['0', '0', '1', '1', '2', '2', '3', '3', '4', '4', '5', '5', '6', '6', '7', '7', '8', '8', '9', '9', '10', '10', '11', '11'],
    ActiveAnnotatedValues=['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11'],
    IndexedColors=[1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 1.0, 1.0, 0.0, 1.0, 0.0, 1.0, 0.0, 1.0, 1.0, 0.63, 0.63, 1.0, 0.67, 0.5, 0.33, 1.0, 0.5, 0.75, 0.53, 0.35, 0.7, 1.0, 0.75, 0.5],
)

# get opacity transfer function/opacity map for 'vtkBlockColors'
vtkBlockColorsPWF = GetOpacityTransferFunction('vtkBlockColors')

# trace defaults for the display properties.
a77d766177c585bcc5a218dbb61737d5955eecaseDisplay.Set(
    Representation='Surface',
    ColorArrayName=['FIELD', 'vtkBlockColors'],
    LookupTable=vtkBlockColorsLUT,
    TextureTransform='Transform2',
    OSPRayScaleArray='nodeDisplacements',
    OSPRayScaleFunction='Piecewise Function',
    Assembly='Hierarchy',
    ScaleFactor=50.0,
    GlyphType='Arrow',
    GaussianRadius=2.5,
    SetScaleArray=['POINTS', 'nodeDisplacements'],
    ScaleTransferFunction='Piecewise Function',
    OpacityArray=['POINTS', 'nodeDisplacements'],
    OpacityTransferFunction='Piecewise Function',
    DataAxesGrid='Grid Axes Representation',
    PolarAxes='Polar Axes Representation',
    ScalarOpacityFunction=vtkBlockColorsPWF,
    ScalarOpacityUnitDistance=10.813793934940971,
    OpacityArrayName=['POINTS', 'nodeDisplacements'],
    SelectInputVectors=['POINTS', 'nodeDisplacements'],
)

# init the 'Piecewise Function' selected for 'ScaleTransferFunction'
a77d766177c585bcc5a218dbb61737d5955eecaseDisplay.ScaleTransferFunction.Points = [-0.0007609481690451503, 0.0, 0.5, 0.0, 0.06293996423482895, 1.0, 0.5, 0.0]

# init the 'Piecewise Function' selected for 'OpacityTransferFunction'
a77d766177c585bcc5a218dbb61737d5955eecaseDisplay.OpacityTransferFunction.Points = [-0.0007609481690451503, 0.0, 0.5, 0.0, 0.06293996423482895, 1.0, 0.5, 0.0]

# show data from extractBlock1
extractBlock1Display = Show(extractBlock1, renderView1, 'GeometryRepresentation')

# trace defaults for the display properties.
extractBlock1Display.Set(
    Representation='Surface',
    ColorArrayName=[None, ''],
    TextureTransform='Transform2',
    OSPRayScaleFunction='Piecewise Function',
    Assembly='Hierarchy',
    ScaleFactor=-2.0000000000000002e+298,
    GlyphType='Arrow',
    GaussianRadius=-1e+297,
    SetScaleArray=[None, ''],
    ScaleTransferFunction='Piecewise Function',
    OpacityArray=[None, ''],
    OpacityTransferFunction='Piecewise Function',
    DataAxesGrid='Grid Axes Representation',
    PolarAxes='Polar Axes Representation',
    SelectInputVectors=[None, ''],
)

# show data from warpByVector1
warpByVector1Display = Show(warpByVector1, renderView1, 'UnstructuredGridRepresentation')

# get 2D transfer function for 'I1p'
i1pTF2D = GetTransferFunction2D('I1p')
i1pTF2D.Set(
    ScalarRangeInitialized=1,
    Range=[0.0, 0.05, 0.0, 1.0],
)

# get color transfer function/color map for 'I1p'
i1pLUT = GetColorTransferFunction('I1p')
i1pLUT.Set(
    AutomaticRescaleRangeMode='Never',
    TransferFunction2D=i1pTF2D,
    RGBPoints=GenerateRGBPoints(
        range_min=0.0,
        range_max=0.05,
    ),
    ScalarRangeInitialized=1.0,
)

# get opacity transfer function/opacity map for 'I1p'
i1pPWF = GetOpacityTransferFunction('I1p')
i1pPWF.Set(
    Points=[0.0, 0.0, 0.5, 0.0, 0.05, 1.0, 0.5, 0.0],
    ScalarRangeInitialized=1,
)

# trace defaults for the display properties.
warpByVector1Display.Set(
    Representation='Surface With Edges',
    ColorArrayName=['CELLS', 'I1p'],
    LookupTable=i1pLUT,
    TextureTransform='Transform2',
    OSPRayScaleArray='nodeDisplacements',
    OSPRayScaleFunction='Piecewise Function',
    Assembly='Hierarchy',
    SelectOrientationVectors='nodeDisplacements',
    ScaleFactor=50.0,
    GlyphType='Arrow',
    GaussianRadius=2.5,
    SetScaleArray=['POINTS', 'nodeDisplacements'],
    ScaleTransferFunction='Piecewise Function',
    OpacityArray=['POINTS', 'nodeDisplacements'],
    OpacityTransferFunction='Piecewise Function',
    DataAxesGrid='Grid Axes Representation',
    PolarAxes='Polar Axes Representation',
    ScalarOpacityFunction=i1pPWF,
    ScalarOpacityUnitDistance=26.468755984598584,
    OpacityArrayName=['POINTS', 'nodeDisplacements'],
    SelectInputVectors=['POINTS', 'nodeDisplacements'],
)

# init the 'Piecewise Function' selected for 'ScaleTransferFunction'
warpByVector1Display.ScaleTransferFunction.Points = [-0.0007609481690451503, 0.0, 0.5, 0.0, 0.06293996423482895, 1.0, 0.5, 0.0]

# init the 'Piecewise Function' selected for 'OpacityTransferFunction'
warpByVector1Display.OpacityTransferFunction.Points = [-0.0007609481690451503, 0.0, 0.5, 0.0, 0.06293996423482895, 1.0, 0.5, 0.0]

# show data from temporalInterpolator1
temporalInterpolator1Display = Show(temporalInterpolator1, renderView1, 'UnstructuredGridRepresentation')

# trace defaults for the display properties.
temporalInterpolator1Display.Set(
    Representation='Surface',
    ColorArrayName=['CELLS', 'I1p'],
    LookupTable=i1pLUT,
    TextureTransform='Transform2',
    OSPRayScaleArray='nodeDisplacements',
    OSPRayScaleFunction='Piecewise Function',
    Assembly='Hierarchy',
    SelectOrientationVectors='nodeDisplacements',
    ScaleFactor=66.000439453125,
    GlyphType='Arrow',
    GaussianRadius=3.30002197265625,
    SetScaleArray=['POINTS', 'nodeDisplacements'],
    ScaleTransferFunction='Piecewise Function',
    OpacityArray=['POINTS', 'nodeDisplacements'],
    OpacityTransferFunction='Piecewise Function',
    DataAxesGrid='Grid Axes Representation',
    PolarAxes='Polar Axes Representation',
    ScalarOpacityFunction=i1pPWF,
    ScalarOpacityUnitDistance=28.88265379154471,
    OpacityArrayName=['POINTS', 'nodeDisplacements'],
    SelectInputVectors=['POINTS', 'nodeDisplacements'],
)

# init the 'Piecewise Function' selected for 'ScaleTransferFunction'
temporalInterpolator1Display.ScaleTransferFunction.Points = [-3.516622790038749e-35, 0.0, 0.5, 0.0, 0.03434807434678078, 1.0, 0.5, 0.0]

# init the 'Piecewise Function' selected for 'OpacityTransferFunction'
temporalInterpolator1Display.OpacityTransferFunction.Points = [-3.516622790038749e-35, 0.0, 0.5, 0.0, 0.03434807434678078, 1.0, 0.5, 0.0]

# show data from generateTimeSteps1
generateTimeSteps1Display = Show(generateTimeSteps1, renderView1, 'UnstructuredGridRepresentation')

# trace defaults for the display properties.
generateTimeSteps1Display.Set(
    Representation='Surface With Edges',
    ColorArrayName=['CELLS', 'I1p'],
    LookupTable=i1pLUT,
    TextureTransform='Transform2',
    EdgeColor=[0.26274511218070984, 0.26274511218070984, 0.26274511218070984],
    NonlinearSubdivisionLevel=0,
    OSPRayScaleArray='nodeDisplacements',
    OSPRayScaleFunction='Piecewise Function',
    Assembly='Hierarchy',
    SelectOrientationVectors='nodeDisplacements',
    ScaleFactor=66.000439453125,
    GlyphType='Arrow',
    GaussianRadius=3.30002197265625,
    SetScaleArray=['POINTS', 'nodeDisplacements'],
    ScaleTransferFunction='Piecewise Function',
    OpacityArray=['POINTS', 'nodeDisplacements'],
    OpacityTransferFunction='Piecewise Function',
    DataAxesGrid='Grid Axes Representation',
    PolarAxes='Polar Axes Representation',
    ScalarOpacityFunction=i1pPWF,
    ScalarOpacityUnitDistance=28.88265379154471,
    OpacityArrayName=['POINTS', 'nodeDisplacements'],
    SelectInputVectors=['POINTS', 'nodeDisplacements'],
)

# init the 'Piecewise Function' selected for 'ScaleTransferFunction'
generateTimeSteps1Display.ScaleTransferFunction.Points = [-3.516622790038749e-35, 0.0, 0.5, 0.0, 0.03434807434678078, 1.0, 0.5, 0.0]

# init the 'Piecewise Function' selected for 'OpacityTransferFunction'
generateTimeSteps1Display.OpacityTransferFunction.Points = [-3.516622790038749e-35, 0.0, 0.5, 0.0, 0.03434807434678078, 1.0, 0.5, 0.0]

# show data from reflect1
reflect1Display = Show(reflect1, renderView1, 'UnstructuredGridRepresentation')

# trace defaults for the display properties.
reflect1Display.Set(
    Representation='Surface',
    ColorArrayName=['CELLS', 'I1p'],
    LookupTable=i1pLUT,
    TextureTransform='Transform2',
    OSPRayScaleArray='nodeDisplacements',
    OSPRayScaleFunction='Piecewise Function',
    Assembly='Hierarchy',
    SelectOrientationVectors='nodeDisplacements',
    ScaleFactor=132.92247009277344,
    GlyphType='Arrow',
    GaussianRadius=6.646123504638672,
    SetScaleArray=['POINTS', 'nodeDisplacements'],
    ScaleTransferFunction='Piecewise Function',
    OpacityArray=['POINTS', 'nodeDisplacements'],
    OpacityTransferFunction='Piecewise Function',
    DataAxesGrid='Grid Axes Representation',
    PolarAxes='Polar Axes Representation',
    ScalarOpacityFunction=i1pPWF,
    ScalarOpacityUnitDistance=34.54899145943267,
    OpacityArrayName=['POINTS', 'nodeDisplacements'],
    SelectInputVectors=['POINTS', 'nodeDisplacements'],
)

# init the 'Piecewise Function' selected for 'ScaleTransferFunction'
reflect1Display.ScaleTransferFunction.Points = [-5.387671947479248, 0.0, 0.5, 0.0, 5.387671947479248, 1.0, 0.5, 0.0]

# init the 'Piecewise Function' selected for 'OpacityTransferFunction'
reflect1Display.OpacityTransferFunction.Points = [-5.387671947479248, 0.0, 0.5, 0.0, 5.387671947479248, 1.0, 0.5, 0.0]

# show data from warpByVector2
warpByVector2Display = Show(warpByVector2, renderView1, 'UnstructuredGridRepresentation')

# trace defaults for the display properties.
warpByVector2Display.Set(
    Representation='Surface',
    ColorArrayName=['CELLS', 'I1p'],
    LookupTable=i1pLUT,
    Opacity=0.4,
    TextureTransform='Transform2',
    EdgeColor=[0.14901961386203766, 0.14901961386203766, 0.14901961386203766],
    NonlinearSubdivisionLevel=0,
    OSPRayScaleArray='nodeDisplacements',
    OSPRayScaleFunction='Piecewise Function',
    Assembly='Hierarchy',
    SelectOrientationVectors='nodeDisplacements',
    ScaleFactor=132.00028076171876,
    GlyphType='Arrow',
    GaussianRadius=6.600014038085938,
    SetScaleArray=['POINTS', 'nodeDisplacements'],
    ScaleTransferFunction='Piecewise Function',
    OpacityArray=['POINTS', 'nodeDisplacements'],
    OpacityTransferFunction='Piecewise Function',
    DataAxesGrid='Grid Axes Representation',
    PolarAxes='Polar Axes Representation',
    ScalarOpacityFunction=i1pPWF,
    ScalarOpacityUnitDistance=34.414988675572275,
    OpacityArrayName=['POINTS', 'nodeDisplacements'],
    SelectInputVectors=['POINTS', 'nodeDisplacements'],
)

# init the 'Piecewise Function' selected for 'ScaleTransferFunction'
warpByVector2Display.ScaleTransferFunction.Points = [-0.445186585187912, 0.0, 0.5, 0.0, 5.387671947479248, 1.0, 0.5, 0.0]

# init the 'Piecewise Function' selected for 'OpacityTransferFunction'
warpByVector2Display.OpacityTransferFunction.Points = [-0.445186585187912, 0.0, 0.5, 0.0, 5.387671947479248, 1.0, 0.5, 0.0]

# show data from threshold1
threshold1Display = Show(threshold1, renderView1, 'UnstructuredGridRepresentation')

# trace defaults for the display properties.
threshold1Display.Set(
    Representation='Surface With Edges',
    ColorArrayName=['CELLS', 'I1p'],
    LookupTable=i1pLUT,
    TextureTransform='Transform2',
    EdgeColor=[0.26274511218070984, 0.26274511218070984, 0.26274511218070984],
    NonlinearSubdivisionLevel=0,
    OSPRayScaleArray='nodeDisplacements',
    OSPRayScaleFunction='Piecewise Function',
    Assembly='Hierarchy',
    SelectOrientationVectors='nodeDisplacements',
    ScaleFactor=66.000439453125,
    GlyphType='Arrow',
    GaussianRadius=3.30002197265625,
    SetScaleArray=['POINTS', 'nodeDisplacements'],
    ScaleTransferFunction='Piecewise Function',
    OpacityArray=['POINTS', 'nodeDisplacements'],
    OpacityTransferFunction='Piecewise Function',
    DataAxesGrid='Grid Axes Representation',
    PolarAxes='Polar Axes Representation',
    ScalarOpacityFunction=i1pPWF,
    ScalarOpacityUnitDistance=29.53822588268621,
    OpacityArrayName=['POINTS', 'nodeDisplacements'],
    SelectInputVectors=['POINTS', 'nodeDisplacements'],
)

# init the 'Piecewise Function' selected for 'ScaleTransferFunction'
threshold1Display.ScaleTransferFunction.Points = [-3.110014243137031e-35, 0.0, 0.5, 0.0, 0.04595167189836502, 1.0, 0.5, 0.0]

# init the 'Piecewise Function' selected for 'OpacityTransferFunction'
threshold1Display.OpacityTransferFunction.Points = [-3.110014243137031e-35, 0.0, 0.5, 0.0, 0.04595167189836502, 1.0, 0.5, 0.0]

# setup the color legend parameters for each legend in this view

# get color legend/bar for vtkBlockColorsLUT in view renderView1
vtkBlockColorsLUTColorBar = GetScalarBar(vtkBlockColorsLUT, renderView1)
vtkBlockColorsLUTColorBar.Set(
    Title='vtkBlockColors',
    ComponentTitle='',
)

# set color bar visibility
vtkBlockColorsLUTColorBar.Visibility = 0

# get color legend/bar for i1pLUT in view renderView1
i1pLUTColorBar = GetScalarBar(i1pLUT, renderView1)
i1pLUTColorBar.Set(
    WindowLocation='Any Location',
    Position=[0.8436698717948719, 0.013913043478260861],
    Title='I1p',
    ComponentTitle='',
    ScalarBarLength=0.33000000000000007,
)

# set color bar visibility
i1pLUTColorBar.Visibility = 0

# get 2D transfer function for 'damage'
damageTF2D = GetTransferFunction2D('damage')

# get color transfer function/color map for 'damage'
damageLUT = GetColorTransferFunction('damage')
damageLUT.Set(
    TransferFunction2D=damageTF2D,
    RGBPoints=GenerateRGBPoints(
        range_min=0.20000490546226501,
        range_max=0.9900000095367432,
    ),
    ScalarRangeInitialized=1.0,
)

# get color legend/bar for damageLUT in view renderView1
damageLUTColorBar = GetScalarBar(damageLUT, renderView1)
damageLUTColorBar.Set(
    Title='damage',
    ComponentTitle='',
)

# set color bar visibility
damageLUTColorBar.Visibility = 0

# hide data in view
Hide(a77d766177c585bcc5a218dbb61737d5955eecase, renderView1)

# hide data in view
Hide(extractBlock1, renderView1)

# hide data in view
Hide(warpByVector1, renderView1)

# hide data in view
Hide(temporalInterpolator1, renderView1)

# hide data in view
Hide(reflect1, renderView1)

# ----------------------------------------------------------------
# setup color maps and opacity maps used in the visualization
# note: the Get..() functions create a new object, if needed
# ----------------------------------------------------------------

# get opacity transfer function/opacity map for 'damage'
damagePWF = GetOpacityTransferFunction('damage')
damagePWF.Set(
    Points=[0.20000490546226501, 0.0, 0.5, 0.0, 0.9900000095367432, 1.0, 0.5, 0.0],
    ScalarRangeInitialized=1,
)

# ----------------------------------------------------------------
# setup animation scene, tracks and keyframes
# note: the Get..() functions create a new object, if needed
# ----------------------------------------------------------------

# get camera animation track for the view
cameraAnimationCue1 = GetCameraTrack(view=renderView1)

# create a new key frame
keyFrame20503 = CameraKeyFrame()
keyFrame20503.Set(
    KeyTime=0.4978866125853405,
    Position=[579.532, 355.847, 314.605],
    PositionPathPoints=[579.532, 355.847, 314.605, 667.5420170952527, 355.847, -131.8503163890106, 373.36254334740215, 355.847, -479.0196552807911, -81.48327734375826, 355.847, -465.477423525908, -354.48726483391715, 355.847, -101.42119784697329, -240.07184827652327, 355.847, 339.0072584261385, 175.6058300115435, 355.847, 524.1563346165444],
    FocalPathPoints=[160.0, 0.0, 0.0],
    ClosedPositionPath=1,
)

# create a new key frame
keyFrame20504 = CameraKeyFrame()
keyFrame20504.KeyTime = 1.0

# initialize the animation scene
cameraAnimationCue1.Set(
    Mode='Path-based',
    KeyFrames=[keyFrame20503, keyFrame20504],
)

# initialize the animation scene
keyFrame20504.KeyTime = 1.0

# create a new key frame
keyFrame22376 = CompositeKeyFrame()
keyFrame22376.Set(
    KeyTime=0.49999999999999994,
    Interpolation='Exponential',
    StartPower=6.0,
    EndPower=2.0,
)

# initialize the animation scene
keyFrame22376.Set(
    KeyTime=0.49999999999999994,
    Interpolation='Exponential',
    StartPower=6.0,
    EndPower=2.0,
)

# create a new key frame
keyFrame22373 = CompositeKeyFrame()
keyFrame22373.Set(
    KeyTime=1.0,
    KeyValues=[0.4],
)

# initialize the animation scene
keyFrame22373.Set(
    KeyTime=1.0,
    KeyValues=[0.4],
)

 # get animation representation helper for 'threshold1'
threshold1RepresentationAnimationHelper = GetRepresentationAnimationHelper(threshold1)

# get animation track
threshold1RepresentationAnimationHelperOpacityTrack = GetAnimationTrack('Opacity', index=0, proxy=threshold1RepresentationAnimationHelper)

# create a new key frame
keyFrame22378 = CompositeKeyFrame()

# create a new key frame
keyFrame22377 = CompositeKeyFrame()
keyFrame22377.Set(
    KeyTime=1.0,
    KeyValues=[1.0],
)

# initialize the animation scene
threshold1RepresentationAnimationHelperOpacityTrack.KeyFrames = [keyFrame22378, keyFrame22376, keyFrame22377]

# get time animation track
timeAnimationCue1 = GetTimeTrack()

# initialize the animation scene

# get the time-keeper
timeKeeper1 = GetTimeKeeper()

# initialize the timekeeper
timeKeeper1.SuppressedTimeSources = a77d766177c585bcc5a218dbb61737d5955eecase

# initialize the animation track

# initialize the animation track
cameraAnimationCue1.Set(
    Mode='Path-based',
    KeyFrames=[keyFrame20503, keyFrame20504],
)

 # get animation representation helper for 'warpByVector2'
warpByVector2RepresentationAnimationHelper = GetRepresentationAnimationHelper(warpByVector2)

# get animation track
warpByVector2RepresentationAnimationHelperOpacityTrack = GetAnimationTrack('Opacity', index=0, proxy=warpByVector2RepresentationAnimationHelper)

# create a new key frame
keyFrame22374 = CompositeKeyFrame()

# create a new key frame
keyFrame22372 = CompositeKeyFrame()
keyFrame22372.Set(
    KeyTime=0.49999999999999994,
    Interpolation='Exponential',
    Base=10.0,
    StartPower=6.0,
    EndPower=2.0,
)

# initialize the animation track
warpByVector2RepresentationAnimationHelperOpacityTrack.KeyFrames = [keyFrame22374, keyFrame22372, keyFrame22373]

# initialize the animation track
threshold1RepresentationAnimationHelperOpacityTrack.KeyFrames = [keyFrame22378, keyFrame22376, keyFrame22377]

# get animation scene
animationScene1 = GetAnimationScene()

# initialize the animation scene
animationScene1.Set(
    ViewModules=renderView1,
    Cues=[timeAnimationCue1, cameraAnimationCue1, warpByVector2RepresentationAnimationHelperOpacityTrack, threshold1RepresentationAnimationHelperOpacityTrack],
    AnimationTime=2.0,
    StartTime=0.0084179688,
    EndTime=2.0,
    PlayMode='Snap To TimeSteps',
)

# initialize the animation scene
keyFrame22377.Set(
    KeyTime=1.0,
    KeyValues=[1.0],
)

# initialize the animation scene
keyFrame20503.Set(
    KeyTime=0.4978866125853405,
    Position=[579.532, 355.847, 314.605],
    PositionPathPoints=[579.532, 355.847, 314.605, 667.5420170952527, 355.847, -131.8503163890106, 373.36254334740215, 355.847, -479.0196552807911, -81.48327734375826, 355.847, -465.477423525908, -354.48726483391715, 355.847, -101.42119784697329, -240.07184827652327, 355.847, 339.0072584261385, 175.6058300115435, 355.847, 524.1563346165444],
    FocalPathPoints=[160.0, 0.0, 0.0],
    ClosedPositionPath=1,
)

# initialize the animation scene
warpByVector2RepresentationAnimationHelperOpacityTrack.KeyFrames = [keyFrame22374, keyFrame22372, keyFrame22373]

# initialize the animation scene
keyFrame22372.Set(
    KeyTime=0.49999999999999994,
    Interpolation='Exponential',
    Base=10.0,
    StartPower=6.0,
    EndPower=2.0,
)

# initialize the animation scene

# initialize the animation scene

# ----------------------------------------------------------------
# restore active source
SetActiveSource(None)
# ----------------------------------------------------------------


##--------------------------------------------
## You may need to add some code at the end of this python script depending on your usage, eg:
#
## Render all views to see them appears
# RenderAllViews()
#
## Interact with the view, usefull when running from pvpython
# Interact()
#
## Save a screenshot of the active view
# SaveScreenshot("path/to/screenshot.png")
#
## Save a screenshot of a layout (multiple splitted view)
# SaveScreenshot("path/to/screenshot.png", GetLayout())
#
## Save all "Extractors" from the pipeline browser
# SaveExtracts()
#
## Save a animation of the current active view
# SaveAnimation()
#
## Please refer to the documentation of paraview.simple
## https://www.paraview.org/paraview-docs/nightly/python/
##--------------------------------------------
