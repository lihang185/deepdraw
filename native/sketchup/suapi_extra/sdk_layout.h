#pragma once
// Private thumbnail prefix for the pinned SketchUp SDK only.
#include <cstdint>

union STLStringData
{
	unsigned __int16* str_buffer;
	unsigned __int16 inl_data[8];
};

struct STLString
{
	STLStringData data;
	__int64 string_length;
	__int64 buffer_length;
};

struct CVector3D
{
	double x, y, z;
};

struct CCamera
{
	__int64 vftable;
	CVector3D eye;
	CVector3D target;
	CVector3D up;
	double v24;
	double v25;
	bool is_perspective;
	double fov;
	double height;
	double aspect_ratio;
	bool fov_is_height;
	double b;
	double c;
	double d;
	STLString description;
	double image_width;
	bool is_2d;
	double scale_2d;
	double center_2d_x;
	double center_2d_y;
};

struct sGUID
{
	unsigned int Data1;
	unsigned __int16 Data2;
	unsigned __int16 Data3;
	unsigned __int8 Data4[8];
};

struct CDib_Buffer
{
	void* file_buf;
	int buf_len;
	int unknow08;
	int version;
	bool b_unknow10;
	int unknow14;
	int unknow18;
	int unknow1C;
	int unknow20;
	int unknow24;
	int unknow28;
	int unknow2C;
};

struct CDib
{
	__int64 vftable;
	CDib_Buffer* data_buffer;
	int ref_count;
	int _pad14_;
	__int64 ImageRep;
	bool unknow20;
	int _pad2_;
	__int64 unknow_ptr_2;
	__int64 unknow_ptr_3;
	int unknow30;
};

struct CSketchupModel
{
	__int64 vftable;
	__int64 ICDBListener;
	bool has_observer;
	bool always_zero;
	STLString name1;
	STLString name2;
	__int64 attributes;
	void* entities;
	__int64 SketchCS;
	__int64 SchemaManager;
	CCamera camera;
	__int64 RenderingOptions;
	__int64 ShadowInfo;
	__int64 OptionsManager;
	__int64 PageList;
	__int64 StyleManager;
	__int64 CWatermarkManager;
	sGUID version_data;
	__int64 ComponentBehavior;
	CDib* cdib;
	CDib* cdib_2;
};
