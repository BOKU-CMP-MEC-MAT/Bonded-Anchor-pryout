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
light3 = CreateLight()
light3.Set(
    Intensity=1.2,
    Type='Positional',
    Position=[-294.24724854788036, 276.1452691232931, 107.47499260879844],
    FocalPoint=[65.56758725084825, -130.64841294565775, -252.25722398242283],
    ConeAngle=40.5,
)

# get the material library
materialLibrary1 = GetMaterialLibrary()

# create light
# Create a new 'Render View'
renderView1 = CreateView('RenderView')
renderView1.Set(
    ViewSize=[2544, 1048],
    AxesGrid='Grid Axes 3D Actor',
    CenterOfRotation=[0.0, -67.72229766845703, -124.9918262064457],
    StereoType='Crystal Eyes',
    CameraPosition=[10.226979823960853, 150.0, 311.35055175846844],
    CameraFocalPoint=[0.02766132354736328, -16.979347229003906, -16.00005342059012],
    CameraFocalDisk=1.0,
    CameraParallelScale=1.0,
    LegendGrid='Legend Grid Actor',
    PolarGrid='Polar Grid Actor',
    Background=[0.329, 0.349, 0.427],
    BackEnd='OSPRay pathtracer',
    SamplesPerPixel=4,
    LightScale=0.2,
    EnvironmentalBG=[0.329, 0.349, 0.427],
    AdditionalLights=light3,
    OSPRayMaterialLibrary=materialLibrary1,
)

SetActiveView(None)

# ----------------------------------------------------------------
# setup view layouts
# ----------------------------------------------------------------

# create new layout object 'Layout #1'
layout1 = CreateLayout(name='Layout #1')
layout1.AssignView(0, renderView1)
layout1.SetSize(2544, 1048)

# ----------------------------------------------------------------
# restore active view
SetActiveView(renderView1)
# ----------------------------------------------------------------

# ----------------------------------------------------------------
# setup the data processing pipelines
# ----------------------------------------------------------------

# create a new 'EnSight Reader'
anchorPryOutcase = EnSightReader(registrationName='AnchorPryOut.case', CaseFileName='/home/matthias/constitutive_modeling/Bonded-Anchor-pryout/FE-GCDP-model/Bonded_anchor_hef_50_d_16/AnchorPryOut.case')
anchorPryOutcase.Set(
    CellArrays=['alphaP', 'alphaD', 'damage', 'I1p'],
    PointArrays=['nodeDisplacements', 'nodeReactionForces', 'nonlocalDamage'],
)

# create a new 'Extract Block'
extractBlock1 = ExtractBlock(registrationName='ExtractBlock1', Input=anchorPryOutcase)
extractBlock1.Set(
    Assembly='Hierarchy',
    Selectors=['/Root/ASSEMBLY_CONCRETE1_CONCRETE', '/Root/ASSEMBLY_STEEL1_MORTAR', '/Root/ASSEMBLY_STEEL1_STEEL'],
)

# create a new 'Warp By Vector'
warpByVector1 = WarpByVector(registrationName='WarpByVector1', Input=extractBlock1)
warpByVector1.Vectors = ['POINTS', 'nodeDisplacements']

# create a new 'Temporal Interpolator'
temporalInterpolator1 = TemporalInterpolator(registrationName='TemporalInterpolator1', Input=warpByVector1)
temporalInterpolator1.DiscreteTimeStepInterval = 0.01

# create a new 'Extract Block'
extractBlock2 = ExtractBlock(registrationName='ExtractBlock2', Input=temporalInterpolator1)
extractBlock2.Set(
    Assembly='Hierarchy',
    Selectors=['/Root/ASSEMBLY_CONCRETE1_CONCRETE'],
)

# create a new 'Extract Block'
extractBlock3 = ExtractBlock(registrationName='ExtractBlock3', Input=temporalInterpolator1)
extractBlock3.Set(
    Assembly='Hierarchy',
    Selectors=['/Root/ASSEMBLY_STEEL1_STEEL'],
)

# create a new 'Generate Time Steps'
generateTimeSteps1 = GenerateTimeSteps(registrationName='GenerateTimeSteps1', Input=extractBlock3)
generateTimeSteps1.TimeStepValues = [1.0, 1.0050251256281406, 1.0100502512562815, 1.015075376884422, 1.020100502512563, 1.0251256281407035, 1.0301507537688441, 1.035175879396985, 1.0402010050251256, 1.0452261306532664, 1.050251256281407, 1.0552763819095476, 1.0603015075376885, 1.065326633165829, 1.07035175879397, 1.0753768844221105, 1.0804020100502512, 1.085427135678392, 1.0904522613065326, 1.0954773869346734, 1.100502512562814, 1.1055276381909547, 1.1105527638190955, 1.1155778894472361, 1.120603015075377, 1.1256281407035176, 1.1306532663316582, 1.135678391959799, 1.1407035175879396, 1.1457286432160805, 1.150753768844221, 1.1557788944723617, 1.1608040201005025, 1.1658291457286432, 1.170854271356784, 1.1758793969849246, 1.1809045226130652, 1.185929648241206, 1.1909547738693467, 1.1959798994974875, 1.2010050251256281, 1.2060301507537687, 1.2110552763819096, 1.2160804020100502, 1.221105527638191, 1.2261306532663316, 1.2311557788944723, 1.236180904522613, 1.2412060301507537, 1.2462311557788945, 1.2512562814070352, 1.2562814070351758, 1.2613065326633166, 1.2663316582914572, 1.271356783919598, 1.2763819095477387, 1.2814070351758793, 1.2864321608040201, 1.2914572864321607, 1.2964824120603016, 1.3015075376884422, 1.3065326633165828, 1.3115577889447236, 1.3165829145728642, 1.321608040201005, 1.3266331658291457, 1.3316582914572863, 1.3366834170854272, 1.3417085427135678, 1.3467336683417086, 1.3517587939698492, 1.3567839195979898, 1.3618090452261307, 1.3668341708542713, 1.3718592964824121, 1.3768844221105527, 1.3819095477386933, 1.3869346733668342, 1.391959798994975, 1.3969849246231156, 1.4020100502512562, 1.4070351758793969, 1.4120603015075377, 1.4170854271356785, 1.4221105527638191, 1.4271356783919598, 1.4321608040201004, 1.4371859296482412, 1.442211055276382, 1.4472361809045227, 1.4522613065326633, 1.457286432160804, 1.4623115577889447, 1.4673366834170856, 1.4723618090452262, 1.4773869346733668, 1.4824120603015074, 1.4874371859296482, 1.492462311557789, 1.4974874371859297, 1.5025125628140703, 1.507537688442211, 1.5125628140703518, 1.5175879396984926, 1.5226130653266332, 1.5276381909547738, 1.5326633165829144, 1.5376884422110553, 1.542713567839196, 1.5477386934673367, 1.5527638190954773, 1.557788944723618, 1.5628140703517588, 1.5678391959798996, 1.5728643216080402, 1.5778894472361809, 1.5829145728643215, 1.5879396984924623, 1.5929648241206031, 1.5979899497487438, 1.6030150753768844, 1.608040201005025, 1.6130653266331658, 1.6180904522613067, 1.6231155778894473, 1.6281407035175879, 1.6331658291457285, 1.6381909547738693, 1.6432160804020102, 1.6482412060301508, 1.6532663316582914, 1.658291457286432, 1.6633165829145728, 1.6683417085427137, 1.6733668341708543, 1.678391959798995, 1.6834170854271355, 1.6884422110552764, 1.6934673366834172, 1.6984924623115578, 1.7035175879396984, 1.708542713567839, 1.7135678391959799, 1.7185929648241207, 1.7236180904522613, 1.728643216080402, 1.7336683417085426, 1.7386934673366834, 1.7437185929648242, 1.7487437185929648, 1.7537688442211055, 1.7587939698492463, 1.763819095477387, 1.7688442211055277, 1.7738693467336684, 1.778894472361809, 1.7839195979899498, 1.7889447236180904, 1.7939698492462313, 1.7989949748743719, 1.8040201005025125, 1.8090452261306533, 1.814070351758794, 1.8190954773869348, 1.8241206030150754, 1.829145728643216, 1.8341708542713568, 1.8391959798994975, 1.8442211055276383, 1.849246231155779, 1.8542713567839195, 1.8592964824120604, 1.864321608040201, 1.8693467336683418, 1.8743718592964824, 1.879396984924623, 1.8844221105527639, 1.8894472361809045, 1.8944723618090453, 1.899497487437186, 1.9045226130653266, 1.9095477386934674, 1.914572864321608, 1.9195979899497488, 1.9246231155778895, 1.92964824120603, 1.934673366834171, 1.9396984924623115, 1.9447236180904524, 1.949748743718593, 1.9547738693467336, 1.9597989949748744, 1.964824120603015, 1.9698492462311559, 1.9748743718592965, 1.979899497487437, 1.984924623115578, 1.9899497487437188, 1.9949748743718594, 2.0]

# ----------------------------------------------------------------
# setup the visualization in view 'renderView1'
# ----------------------------------------------------------------

# show data from anchorPryOutcase
anchorPryOutcaseDisplay = Show(anchorPryOutcase, renderView1, 'UnstructuredGridRepresentation')

# get 2D transfer function for 'vtkBlockColors'
vtkBlockColorsTF2D = GetTransferFunction2D('vtkBlockColors')

# get color transfer function/color map for 'vtkBlockColors'
vtkBlockColorsLUT = GetColorTransferFunction('vtkBlockColors')
vtkBlockColorsLUT.Set(
    InterpretValuesAsCategories=1,
    AnnotationsInitialized=1,
    TransferFunction2D=vtkBlockColorsTF2D,
    ColorSpace='Diverging',
    Annotations=['0', '0', '1', '1', '2', '2', '3', '3', '4', '4', '5', '5', '6', '6', '7', '7', '8', '8', '9', '9', '10', '10', '11', '11'],
    ActiveAnnotatedValues=['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11'],
    IndexedColors=[1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 1.0, 1.0, 0.0, 1.0, 0.0, 1.0, 0.0, 1.0, 1.0, 0.63, 0.63, 1.0, 0.67, 0.5, 0.33, 1.0, 0.5, 0.75, 0.53, 0.35, 0.7, 1.0, 0.75, 0.5],
)

# get opacity transfer function/opacity map for 'vtkBlockColors'
vtkBlockColorsPWF = GetOpacityTransferFunction('vtkBlockColors')

# trace defaults for the display properties.
anchorPryOutcaseDisplay.Set(
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
anchorPryOutcaseDisplay.ScaleTransferFunction.Points = [-0.0007609481690451503, 0.0, 0.5, 0.0, 0.06293996423482895, 1.0, 0.5, 0.0]

# init the 'Piecewise Function' selected for 'OpacityTransferFunction'
anchorPryOutcaseDisplay.OpacityTransferFunction.Points = [-0.0007609481690451503, 0.0, 0.5, 0.0, 0.06293996423482895, 1.0, 0.5, 0.0]

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
    ColorSpace='Diverging',
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
    Representation='Surface With Edges',
    ColorArrayName=['CELLS', 'I1p'],
    LookupTable=i1pLUT,
    TextureTransform='Transform2',
    NonlinearSubdivisionLevel=0,
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
    ScalarOpacityUnitDistance=20.969552992721756,
    OpacityArrayName=['POINTS', 'nodeDisplacements'],
    SelectInputVectors=['POINTS', 'nodeDisplacements'],
)

# init the 'Piecewise Function' selected for 'ScaleTransferFunction'
temporalInterpolator1Display.ScaleTransferFunction.Points = [-0.02543729357421398, 0.0, 0.5, 0.0, 0.4011745750904083, 1.0, 0.5, 0.0]

# init the 'Piecewise Function' selected for 'OpacityTransferFunction'
temporalInterpolator1Display.OpacityTransferFunction.Points = [-0.02543729357421398, 0.0, 0.5, 0.0, 0.4011745750904083, 1.0, 0.5, 0.0]

# show data from extractBlock3
extractBlock3Display = Show(extractBlock3, renderView1, 'GeometryRepresentation')

# trace defaults for the display properties.
extractBlock3Display.Set(
    Representation='Surface With Edges',
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

# show data from generateTimeSteps1
generateTimeSteps1Display = Show(generateTimeSteps1, renderView1, 'UnstructuredGridRepresentation')

# trace defaults for the display properties.
generateTimeSteps1Display.Set(
    Representation='Surface With Edges',
    ColorArrayName=[None, ''],
    Opacity=0.5,
    TextureTransform='Transform2',
    OSPRayScaleArray='nodeDisplacements',
    OSPRayScaleFunction='Piecewise Function',
    Assembly='Hierarchy',
    SelectOrientationVectors='nodeDisplacements',
    ScaleFactor=6.604030609130859,
    GlyphType='Arrow',
    GaussianRadius=0.330201530456543,
    SetScaleArray=['POINTS', 'nodeDisplacements'],
    ScaleTransferFunction='Piecewise Function',
    OpacityArray=['POINTS', 'nodeDisplacements'],
    OpacityTransferFunction='Piecewise Function',
    DataAxesGrid='Grid Axes Representation',
    PolarAxes='Polar Axes Representation',
    ScalarOpacityUnitDistance=11.12929431178574,
    OpacityArrayName=['POINTS', 'nodeDisplacements'],
    SelectInputVectors=['POINTS', 'nodeDisplacements'],
)

# init the 'Piecewise Function' selected for 'ScaleTransferFunction'
generateTimeSteps1Display.ScaleTransferFunction.Points = [7.170192111516371e-05, 0.0, 0.5, 0.0, 0.037369634956121445, 1.0, 0.5, 0.0]

# init the 'Piecewise Function' selected for 'OpacityTransferFunction'
generateTimeSteps1Display.OpacityTransferFunction.Points = [7.170192111516371e-05, 0.0, 0.5, 0.0, 0.037369634956121445, 1.0, 0.5, 0.0]

# show data from extractBlock2
extractBlock2Display = Show(extractBlock2, renderView1, 'GeometryRepresentation')

# trace defaults for the display properties.
extractBlock2Display.Set(
    Representation='Surface With Edges',
    ColorArrayName=['CELLS', 'I1p'],
    LookupTable=i1pLUT,
    EdgeColor=[0.27450981736183167, 0.27450981736183167, 0.27450981736183167],
    NonlinearSubdivisionLevel=0,
    Assembly='Hierarchy',
    ScaleFactor=-2.0000000000000002e+298,
    GaussianRadius=-1e+297,
    SetScaleArray=[None, ''],
    OpacityArray=[None, ''],
    SelectInputVectors=[None, ''],
)

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
    Position=[0.82119140625, 0.012500000000000011],
    Title='I1p',
    ComponentTitle='',
    ScalarBarLength=0.33000000000000007,
)

# set color bar visibility
i1pLUTColorBar.Visibility = 0

# get 2D transfer function for 'nodeDisplacements'
nodeDisplacementsTF2D = GetTransferFunction2D('nodeDisplacements')

# get color transfer function/color map for 'nodeDisplacements'
nodeDisplacementsLUT = GetColorTransferFunction('nodeDisplacements')
nodeDisplacementsLUT.Set(
    TransferFunction2D=nodeDisplacementsTF2D,
    RGBPoints=GenerateRGBPoints(
        range_min=8.385598131536666e-39,
        range_max=0.05522373559068138,
    ),
    ColorSpace='Diverging',
    ScalarRangeInitialized=1.0,
)

# get color legend/bar for nodeDisplacementsLUT in view renderView1
nodeDisplacementsLUTColorBar = GetScalarBar(nodeDisplacementsLUT, renderView1)
nodeDisplacementsLUTColorBar.Set(
    Title='nodeDisplacements',
    ComponentTitle='Magnitude',
)

# set color bar visibility
nodeDisplacementsLUTColorBar.Visibility = 0

# get 2D transfer function for 'nonlocalDamage'
nonlocalDamageTF2D = GetTransferFunction2D('nonlocalDamage')

# get color transfer function/color map for 'nonlocalDamage'
nonlocalDamageLUT = GetColorTransferFunction('nonlocalDamage')
nonlocalDamageLUT.Set(
    TransferFunction2D=nonlocalDamageTF2D,
    RGBPoints=GenerateRGBPoints(
        range_min=-2.3389596805049352e-14,
        range_max=0.0046303169801831245,
    ),
    ColorSpace='Diverging',
    ScalarRangeInitialized=1.0,
)

# get color legend/bar for nonlocalDamageLUT in view renderView1
nonlocalDamageLUTColorBar = GetScalarBar(nonlocalDamageLUT, renderView1)
nonlocalDamageLUTColorBar.Set(
    Title='nonlocalDamage',
    ComponentTitle='',
)

# set color bar visibility
nonlocalDamageLUTColorBar.Visibility = 0

# get 2D transfer function for 'damage'
damageTF2D = GetTransferFunction2D('damage')

# get color transfer function/color map for 'damage'
damageLUT = GetColorTransferFunction('damage')
damageLUT.Set(
    TransferFunction2D=damageTF2D,
    RGBPoints=GenerateRGBPoints(
        range_min=0.0,
        range_max=0.9900000095367432,
    ),
    ColorSpace='Diverging',
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
Hide(anchorPryOutcase, renderView1)

# hide data in view
Hide(extractBlock1, renderView1)

# hide data in view
Hide(warpByVector1, renderView1)

# hide data in view
Hide(temporalInterpolator1, renderView1)

# hide data in view
Hide(extractBlock3, renderView1)

# ----------------------------------------------------------------
# setup color maps and opacity maps used in the visualization
# note: the Get..() functions create a new object, if needed
# ----------------------------------------------------------------

# get opacity transfer function/opacity map for 'nonlocalDamage'
nonlocalDamagePWF = GetOpacityTransferFunction('nonlocalDamage')
nonlocalDamagePWF.Set(
    Points=[-2.3389596805049352e-14, 0.0, 0.5, 0.0, 0.0046303169801831245, 1.0, 0.5, 0.0],
    ScalarRangeInitialized=1,
)

# get opacity transfer function/opacity map for 'nodeDisplacements'
nodeDisplacementsPWF = GetOpacityTransferFunction('nodeDisplacements')
nodeDisplacementsPWF.Set(
    Points=[8.385598131536666e-39, 0.0, 0.5, 0.0, 0.05522373559068138, 1.0, 0.5, 0.0],
    ScalarRangeInitialized=1,
)

# get opacity transfer function/opacity map for 'damage'
damagePWF = GetOpacityTransferFunction('damage')
damagePWF.Set(
    Points=[0.0, 0.0, 0.5, 0.0, 0.9900000095367432, 1.0, 0.5, 0.0],
    ScalarRangeInitialized=1,
)

# ----------------------------------------------------------------
# setup animation scene, tracks and keyframes
# note: the Get..() functions create a new object, if needed
# ----------------------------------------------------------------

# create a new key frame
keyFrame21631 = CameraKeyFrame()
keyFrame21631.Set(
    KeyTime=0.49874932080883844,
    Position=[0.0, 150.0, 311.521],
    PositionPathPoints=[0.0, 150.0, 311.521, 256.07672191410364, 150.0, 188.22759221874045, 319.3432787368047, 150.0, -88.85343328894217, 142.15866277804142, 150.0, -311.0744128928821, -142.0534962377499, 150.0, -311.0984164694279, -319.2756457001839, 150.0, -88.90736883585679, -256.05589239101613, 150.0, 188.1843392683684],
    FocalPathPoints=[0.02766132354736328, -16.979347229003906, -16.00005342059012],
    ClosedPositionPath=1,
)

# initialize the animation scene
keyFrame21631.Set(
    KeyTime=0.49874932080883844,
    Position=[0.0, 150.0, 311.521],
    PositionPathPoints=[0.0, 150.0, 311.521, 256.07672191410364, 150.0, 188.22759221874045, 319.3432787368047, 150.0, -88.85343328894217, 142.15866277804142, 150.0, -311.0744128928821, -142.0534962377499, 150.0, -311.0984164694279, -319.2756457001839, 150.0, -88.90736883585679, -256.05589239101613, 150.0, 188.1843392683684],
    FocalPathPoints=[0.02766132354736328, -16.979347229003906, -16.00005342059012],
    ClosedPositionPath=1,
)

# get time animation track
timeAnimationCue1 = GetTimeTrack()

# initialize the animation scene

# get the time-keeper
timeKeeper1 = GetTimeKeeper()

# initialize the timekeeper
timeKeeper1.SuppressedTimeSources = anchorPryOutcase

# initialize the animation track

 # get animation representation helper for 'generateTimeSteps1'
generateTimeSteps1RepresentationAnimationHelper = GetRepresentationAnimationHelper(generateTimeSteps1)

# get animation track
generateTimeSteps1RepresentationAnimationHelperOpacityTrack = GetAnimationTrack('Opacity', index=0, proxy=generateTimeSteps1RepresentationAnimationHelper)

# create a new key frame
keyFrame21552 = CompositeKeyFrame()
keyFrame21552.Set(
    KeyValues=[1.0],
    Interpolation='Boolean',
)

# create a new key frame
keyFrame21542 = CompositeKeyFrame()
keyFrame21542.Set(
    KeyTime=0.5,
    KeyValues=[0.5],
    Interpolation='Boolean',
)

# create a new key frame
keyFrame21543 = CompositeKeyFrame()
keyFrame21543.Set(
    KeyTime=1.0,
    KeyValues=[0.5],
)

# initialize the animation track
generateTimeSteps1RepresentationAnimationHelperOpacityTrack.KeyFrames = [keyFrame21552, keyFrame21542, keyFrame21543]

# get camera animation track for the view
cameraAnimationCue1 = GetCameraTrack(view=renderView1)

# create a new key frame
keyFrame21632 = CameraKeyFrame()
keyFrame21632.KeyTime = 1.0

# initialize the animation track
cameraAnimationCue1.Set(
    Mode='Path-based',
    KeyFrames=[keyFrame21631, keyFrame21632],
)

# get animation scene
animationScene1 = GetAnimationScene()

# initialize the animation scene
animationScene1.Set(
    ViewModules=renderView1,
    Cues=[timeAnimationCue1, generateTimeSteps1RepresentationAnimationHelperOpacityTrack, cameraAnimationCue1],
    AnimationTime=1.0049902344,
    StartTime=0.0049902344,
    EndTime=2.0,
    PlayMode='Snap To TimeSteps',
)

# initialize the animation scene
keyFrame21552.Set(
    KeyValues=[1.0],
    Interpolation='Boolean',
)

# initialize the animation scene
keyFrame21542.Set(
    KeyTime=0.5,
    KeyValues=[0.5],
    Interpolation='Boolean',
)

# initialize the animation scene
keyFrame21632.KeyTime = 1.0

# initialize the animation scene
cameraAnimationCue1.Set(
    Mode='Path-based',
    KeyFrames=[keyFrame21631, keyFrame21632],
)

# initialize the animation scene
generateTimeSteps1RepresentationAnimationHelperOpacityTrack.KeyFrames = [keyFrame21552, keyFrame21542, keyFrame21543]

# initialize the animation scene
keyFrame21543.Set(
    KeyTime=1.0,
    KeyValues=[0.5],
)

# ----------------------------------------------------------------
# restore active source
SetActiveSource(extractBlock2)
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