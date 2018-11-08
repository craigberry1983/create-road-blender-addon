bl_info = {
    "name": "Create Road Tool",
    "author": "Craig Berry",
    "location": "View3D > Tools > Create Road",
    "version": (1, 0, 0),
    "blender": (2, 7, 9),
    "description": "Tool for speeding up road object creation.",
    "category": "Development"
    }

import bpy, bmesh, os, mathutils

from bpy.props import (StringProperty,
                       BoolProperty,
                       IntProperty,
                       FloatProperty,
                       EnumProperty,
                       PointerProperty,
                       )
from bpy.types import (Panel,
                       Operator,
                       PropertyGroup,
                       )
					   
road_segment_length = 2.0   



class MySettings(PropertyGroup):

    left_sidewalk = BoolProperty(
        name="Left Sidewalk",
        description="Make a sidewalk on left hand side of road",
        default = True
        )

    right_sidewalk = BoolProperty(
        name="Right Sidewalk",
        description="Make a sidewalk on right hand side of road",
        default = True
        )
		
    gutters = BoolProperty(
        name="Gutters",
        description="Add gutter geometry to sides of the road",
        default = True
        )

    number_lanes = IntProperty(
        name = "Number Lanes",
        description="How many lanes should there be across the whole road",
        default = 2,
        min = 1,
        max = 15
        )
		
    road_name = StringProperty(
        name="Road Name",
        description=":",
        default="Road",
        maxlen=1024,
        )
	
    lane_width = bpy.props.FloatProperty(
            name = "Lane Width",
            description = "Width of a single lane on the road",
            default = 3.7,
            min = 1.0,
            max = 10.0,
            precision = 4
			)
	
    kerb_height = bpy.props.FloatProperty(
            name = "Kerb Height",
            description = "Height of the kerb on both sides of the road",
            default = 0.127,
            min = 0.0,
            max = 1.0,
            precision = 4
			)
    kerb_width = bpy.props.FloatProperty(
            name = "Kerb Width",
            description = "Width of kerb on both sides of the road",
            default = 0.127,
            min = 0.0,
            max = 1.0,
            precision = 4
			)
			
    left_sidewalk_width = bpy.props.FloatProperty(
            name = "Left Sidewalk Width",
            description = "Width of sidewalk on left hand side of road",
            default = 4.0,
            min = 1.0,
            max = 10.0,
            precision = 4
			)
    right_sidewalk_width = bpy.props.FloatProperty(
            name = "Right Sidewalk Width",
            description = "Width of sidewalk on right hand side of road",
            default = 4.0,
            min = 1.0,
            max = 10.0,
            precision = 4
			)	
	
    rotation = bpy.props.FloatProperty(
            name = "Rotation",
            description = "Starting rotation of the road",
            default = 0.0,
            min = 0.0,
            max = 360.0,
            precision = 4
			)
			
#======================================================
#	CREATE ROAD OPERATOR / BUTTON
#======================================================
class CreateRoadOperator(bpy.types.Operator):
	bl_idname = "object.createroadoperator"
	bl_label = "Create Road"

	@staticmethod
	def creatematerial(materialfilename):
		materialobj = bpy.data.materials.get(materialfilename)
		if materialobj is None:
			materialobj = bpy.data.materials.new(name=materialfilename)
			ts = materialobj.texture_slots.add()
			tex = bpy.data.textures.new(materialfilename + "_Texture", 'IMAGE')
			script_file = os.path.realpath(__file__)
			directory = os.path.dirname(script_file)
			img = bpy.data.images.load(directory + "\\" + materialfilename + ".png")
			tex.image = img
			ts.texture = tex
			materialobj.use_shadeless = True
			materialobj.type = 'SURFACE'
		return materialobj
	
	#must be run in edit mode
	@staticmethod
	def GetLeftMostEdgeIndex(bm):
		first = True
		for edge in bm.edges:
			if edge.verts[0].co.x == edge.verts[1].co.x:
				if first:
					leftmostedge = edge
					first = False
				elif leftmostedge.verts[0].co.x > edge.verts[0].co.x:
					leftmostedge = edge
				elif leftmostedge.verts[0].co.x == edge.verts[0].co.x:
					if leftmostedge.verts[0].co.z < edge.verts[0].co.z:
						leftmostedge = edge
						
		return leftmostedge.index
					
	#must be run in edit mode
	@staticmethod
	def GetRightMostEdgeIndex(bm):
		first = True
		for edge in bm.edges:
			if edge.verts[0].co.x == edge.verts[1].co.x:
				if first:
					rightmostedge = edge
					first = False
				elif rightmostedge.verts[0].co.x < edge.verts[0].co.x:
					rightmostedge = edge
				elif rightmostedge.verts[0].co.x == edge.verts[0].co.x:
					if rightmostedge.verts[0].co.z < edge.verts[0].co.z:
						rightmostedge = edge
						
		return rightmostedge.index
		
	#must be run in edit mode
	@staticmethod
	def ApplyMaterialAndUnwrapLastFace(bm, materialIndex, bottomright, topright, topleft, bottomleft):
		bpy.ops.mesh.select_all(action="DESELECT")
		lastfaceindex = len(bm.faces) - 1
		bm.faces.ensure_lookup_table()
		bm.faces[lastfaceindex].select = True   
		bpy.context.active_object.active_material_index = materialIndex
		bpy.ops.object.material_slot_assign()
			
		loop_data = bm.faces[lastfaceindex].loops
		uv_layer = bm.loops.layers.uv.active 
		# bottom right                  
		uv_data = loop_data[0][uv_layer].uv
		uv_data.x = bottomright.x
		uv_data.y = bottomright.y
		# top right                  
		uv_data = loop_data[1][uv_layer].uv
		uv_data.x = topright.x
		uv_data.y = topright.y
		#  top left                                                                                  
		uv_data = loop_data[2][uv_layer].uv
		uv_data.x = topleft.x
		uv_data.y = topleft.y
		# bottom left                  
		uv_data = loop_data[3][uv_layer].uv
		uv_data.x = bottomleft.x
		uv_data.y = bottomleft.y
		
		bpy.ops.mesh.select_all(action="DESELECT")
		
	
	@staticmethod
	def AddSidewalk(self, left, context, bm):
		mytool = context.scene.my_tool

		if left:
			#kerb side
			bm.edges.ensure_lookup_table()
			bm.edges[self.GetLeftMostEdgeIndex(bm)].select = True
			bpy.ops.mesh.extrude_region_move(TRANSFORM_OT_translate = {"value": (0.0, 0.0, mytool.kerb_height), "constraint_axis": (True, True, True), "constraint_orientation" :'GLOBAL'})
			self.ApplyMaterialAndUnwrapLastFace(bm, 1, mathutils.Vector([0.5,0.0]), mathutils.Vector([0.5,2.0]), mathutils.Vector([0.25, 2.0]),mathutils.Vector([0.25,0.0]))
			
			#kerb top
			bm.edges.ensure_lookup_table()
			bm.edges[self.GetLeftMostEdgeIndex(bm)].select = True
			bpy.ops.mesh.extrude_region_move(TRANSFORM_OT_translate = {"value": (-mytool.kerb_width, 0.0, 0.0), "constraint_axis": (True, True, True), "constraint_orientation" :'GLOBAL'})
			self.ApplyMaterialAndUnwrapLastFace(bm, 1, mathutils.Vector([0.25,0.0]), mathutils.Vector([0.25,2.0]), mathutils.Vector([0.0, 2.0]),mathutils.Vector([0.0,0.0]))
			
			#sidewalk
			bm.edges.ensure_lookup_table()
			bm.edges[self.GetLeftMostEdgeIndex(bm)].select = True
			bpy.ops.mesh.extrude_region_move(TRANSFORM_OT_translate = {"value": (-mytool.left_sidewalk_width, 0.0, 0.0), "constraint_axis": (True, True, True), "constraint_orientation" :'GLOBAL'})
			self.ApplyMaterialAndUnwrapLastFace(bm, 2, mathutils.Vector([2.0,0.0]), mathutils.Vector([2.0,2.0]), mathutils.Vector([0.0, 2.0]),mathutils.Vector([0.0,0.0]))

		else: #handle right sidewalk
			#kerb side
			bm.edges.ensure_lookup_table()
			bm.edges[self.GetRightMostEdgeIndex(bm)].select = True
			bpy.ops.mesh.extrude_region_move(TRANSFORM_OT_translate = {"value": (0.0, 0.0, mytool.kerb_height), "constraint_axis": (True, True, True), "constraint_orientation" :'GLOBAL'})
			self.ApplyMaterialAndUnwrapLastFace(bm, 1, mathutils.Vector([0.5,0.0]), mathutils.Vector([0.5,2.0]), mathutils.Vector([0.25, 2.0]),mathutils.Vector([0.25,0.0]))

			#kerb top
			bm.edges.ensure_lookup_table()
			bm.edges[self.GetRightMostEdgeIndex(bm)].select = True
			bpy.ops.mesh.extrude_region_move(TRANSFORM_OT_translate = {"value": (mytool.kerb_width, 0.0, 0.0), "constraint_axis": (True, True, True), "constraint_orientation" :'GLOBAL'})
			self.ApplyMaterialAndUnwrapLastFace(bm, 1, mathutils.Vector([0.25,0.0]), mathutils.Vector([0.25,2.0]), mathutils.Vector([0.0, 2.0]),mathutils.Vector([0.0,0.0]))
			
			#sidewalk
			bm.edges.ensure_lookup_table()
			bm.edges[self.GetRightMostEdgeIndex(bm)].select = True
			bpy.ops.mesh.extrude_region_move(TRANSFORM_OT_translate = {"value": (mytool.right_sidewalk_width, 0.0, 0.0), "constraint_axis": (True, True, True), "constraint_orientation" :'GLOBAL'})
			self.ApplyMaterialAndUnwrapLastFace(bm, 2, mathutils.Vector([2.0,0.0]), mathutils.Vector([2.0,2.0]), mathutils.Vector([0.0, 2.0]),mathutils.Vector([0.0,0.0]))
			
		
	def execute(self, context):
		mytool = context.scene.my_tool
		
		#make materials if they don't already exist
		matsidewalk = self.creatematerial('sidewalk')
		matroad = self.creatematerial('road')
		matkerb = self.creatematerial('kerb')
		
		#add a plane at 3D cursor position but at ground level 
		bpy.ops.mesh.primitive_plane_add(radius=(mytool.lane_width * mytool.number_lanes) * 0.5, view_align=False, enter_editmode=False, location=(bpy.context.scene.cursor_location.x,bpy.context.scene.cursor_location.y,0))

		#rename plane
		bpy.context.active_object.name = mytool.road_name
		
		#add the three materials to the object (I'll UV wrap and assign them to faces in a minute)
		bpy.context.active_object.data.materials.append(matroad)
		bpy.context.active_object.data.materials.append(matkerb)
		bpy.context.active_object.data.materials.append(matsidewalk)

		# Set mode to Edit Mode and deselect everything
		bpy.ops.object.mode_set(mode="EDIT")
		bpy.ops.mesh.select_all(action="DESELECT")

		# Register bmesh object                
		bm = bmesh.from_edit_mesh(bpy.context.object.data)

		#shift mesh so origin is at the end of it where user expects it
		bpy.ops.mesh.select_all(action="SELECT")
		bpy.ops.transform.translate(value = (0, (mytool.lane_width * mytool.number_lanes) * 0.5, 0))
		bpy.ops.mesh.select_all(action="DESELECT")

		#translate "top" of road plane into place
		bm.edges.ensure_lookup_table()
		bm.edges[3].select = True
		ypos = bm.edges[1].verts[0].co.y + road_segment_length
		bm.edges[3].verts[0].co.y = ypos
		bm.edges[3].verts[1].co.y = ypos
		bpy.ops.mesh.select_all(action="DESELECT")
		
		# Unwrap to instantiate uv layer    
		bm.faces.ensure_lookup_table()
		bpy.ops.mesh.select_all(action="SELECT")
		bpy.ops.uv.unwrap()
		bpy.ops.mesh.select_all(action="DESELECT")
		
		#apply road texture to road face
		self.ApplyMaterialAndUnwrapLastFace(bm, 0, mathutils.Vector([mytool.number_lanes,0.0]), mathutils.Vector([mytool.number_lanes,road_segment_length]), mathutils.Vector([0.0,road_segment_length]),mathutils.Vector([0.0,0.0]))
			
		#gutters
		if mytool.gutters:
			#left
			bm.edges.ensure_lookup_table()
			bm.edges[self.GetLeftMostEdgeIndex(bm)].select = True
			bpy.ops.mesh.extrude_region_move(TRANSFORM_OT_translate = {"value": (-mytool.kerb_width * 2, 0.0, 0.0), "constraint_axis": (True, True, True), "constraint_orientation" :'GLOBAL'})
			self.ApplyMaterialAndUnwrapLastFace(bm, 1, mathutils.Vector([1.0,0.0]), mathutils.Vector([1.0,2.0]), mathutils.Vector([0.5, 2.0]),mathutils.Vector([0.5,0.0]))
			
			#right
			bm.edges.ensure_lookup_table()
			bm.edges[self.GetRightMostEdgeIndex(bm)].select = True
			bpy.ops.mesh.extrude_region_move(TRANSFORM_OT_translate = {"value": (mytool.kerb_width * 2, 0.0, 0.0), "constraint_axis": (True, True, True), "constraint_orientation" :'GLOBAL'})
			self.ApplyMaterialAndUnwrapLastFace(bm, 1, mathutils.Vector([0.5,0.0]), mathutils.Vector([0.5,2.0]), mathutils.Vector([1.0, 2.0]),mathutils.Vector([1.0,0.0]))

		if mytool.left_sidewalk:
			self.AddSidewalk(self, True, context, bm)
		
		if mytool.right_sidewalk:
			self.AddSidewalk(self, False, context, bm)
	
		bpy.ops.mesh.loopcut_slide(MESH_OT_loopcut={"number_cuts":1, "smoothness":0, "falloff":'INVERSE_SQUARE', "edge_index":10, "mesh_select_mode_init":(True, False, False)}, TRANSFORM_OT_edge_slide={"value":0, "single_side":False, "use_even":False, "flipped":False, "use_clamp":True, "mirror":False, "snap":False, "snap_target":'CLOSEST', "snap_point":(0, 0, 0), "snap_align":False, "snap_normal":(0, 0, 0), "correct_uv":False, "release_confirm":False, "use_accurate":False})

		
		# Set mode to Object Mode
		bpy.ops.object.mode_set(mode="OBJECT")

		# store name of road object for parenting operation
		roadobjname = bpy.context.active_object.name

		#add path and rotate it 90 degrees
		bpy.ops.curve.primitive_nurbs_path_add(radius=1, view_align=False, enter_editmode=False, location=(0, 0, 0), layers=(True, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False))
		bpy.ops.transform.rotate(value=1.5708, axis=(0, 0, 1), constraint_axis=(False, False, True), constraint_orientation='GLOBAL', mirror=False, proportional='DISABLED', proportional_edit_falloff='SMOOTH', proportional_size=1)
		bpy.ops.transform.translate(value = (0,2,0))
		bpy.context.active_object.name = mytool.road_name + "_curve"
		curveobjname = bpy.context.active_object.name

		#parent path object to road object
		objects = bpy.data.objects
		a = objects[roadobjname]
		bpy.context.active_object.parent = a

		#select no objects, then select road and curve object
		bpy.ops.object.select_all(action='TOGGLE')
		bpy.ops.object.select_all(action='TOGGLE')
		bpy.data.objects[roadobjname].select = True
		bpy.data.objects[curveobjname].select = True
		bpy.context.scene.objects.active = bpy.data.objects[roadobjname]

		#rotate to desired angle
		bpy.ops.transform.rotate(value = (3.14159 * mytool.rotation / 180), axis = (0, 0, 1))

		#select no objects, then select road object
		bpy.ops.object.select_all(action='TOGGLE')
		bpy.ops.object.select_all(action='TOGGLE')
		bpy.data.objects[roadobjname].select = True
		bpy.context.scene.objects.active = bpy.data.objects[roadobjname]
		
		#add an array modifier and setup with the appropriate options
		bpy.ops.object.modifier_add(type='ARRAY')
		bpy.context.object.modifiers["Array"].use_merge_vertices = True
		bpy.context.object.modifiers["Array"].fit_type = 'FIT_CURVE'
		bpy.context.object.modifiers["Array"].curve = bpy.data.objects[curveobjname]
		bpy.context.object.modifiers["Array"].relative_offset_displace[0] = 0
		bpy.context.object.modifiers["Array"].relative_offset_displace[1] = 1

		#add a curve modifier and setup properly
		bpy.ops.object.modifier_add(type='CURVE')
		bpy.context.object.modifiers["Curve"].object = bpy.data.objects[curveobjname]
		
		#select no objects, then select curve object
		bpy.ops.object.select_all(action='TOGGLE')
		bpy.ops.object.select_all(action='TOGGLE')
		bpy.data.objects[roadobjname].select = True
		bpy.context.scene.objects.active = bpy.data.objects[curveobjname]
		# set to edit mode
		bpy.ops.object.mode_set(mode="EDIT")
		
		return{'FINISHED'}

#======================================================
#	PANEL
#======================================================

class CreateRoadPanel(bpy.types.Panel):
    bl_label = "Create Road"
    bl_idname = "3D_VIEW_TS_createroad"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'TOOLS'
    bl_category = "Create Road"

    def draw(self, context):
        layout = self.layout
        mytool = context.scene.my_tool
		
        row = layout.row()
        row.prop(mytool, "road_name")
		
        row = layout.row()
        row.prop(mytool, "rotation")
		
        row = layout.row()
        row.prop(mytool, "number_lanes")
		
        row = layout.row()
        row.prop(mytool, "lane_width")
		
        row = layout.row()
        row.prop(mytool, "gutters")
		
        row = layout.row()
        row.prop(mytool, "left_sidewalk")
		
        row = layout.row()
        row.prop(mytool, "right_sidewalk")
		
        row = layout.row()
        row.prop(mytool, "kerb_width")
		
        row = layout.row()
        row.prop(mytool, "kerb_height")
		
        row = layout.row()
        row.prop(mytool, "left_sidewalk_width")
		
        row = layout.row()
        row.prop(mytool, "right_sidewalk_width")
		
        # put a seperator here or something?
		
        row = layout.row()
        row.operator("object.createroadoperator")
		
		
def register():
	bpy.utils.register_module(__name__)
	bpy.types.Scene.my_tool = bpy.props.PointerProperty(type=MySettings)
	

def unregister():
	bpy.utils.unregister_module(__name__)
	del bpy.types.Scene.my_tool

if __name__ == "__main__":
    register()
