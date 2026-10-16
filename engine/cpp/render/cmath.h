#ifndef _Math_h
#define _Math_h

struct SVector3D;
struct SBoundingBox;
struct SMatrix2;

const double EPS = 0.001;
const double EPS2 = EPS * EPS;
const double INF_MAX = 1e30;

class CVector3D
{
public:
	CVector3D() :x(0), y(0), z(0) {}
	CVector3D(double ix, double iy, double iz) :x(ix), y(iy), z(iz) {}
	CVector3D(const CVector3D& R) :x(R.x), y(R.y), z(R.z) {}
	CVector3D& operator=(const SVector3D& R);
	~CVector3D() {}

	CVector3D operator*(double scale);
	double& operator[](int i);
	bool Normalize();

	CVector3D Cross(CVector3D& R);
	double Dot(CVector3D& R);

	double x;
	double y;
	double z;
};

class CBoundingBox
{
public:
	CBoundingBox();
	CBoundingBox& operator=(const SBoundingBox& R);
	~CBoundingBox() {}

	void Reset();
	SBoundingBox ToSBoundingBox();
	void Extend(CVector3D& p);
	CVector3D GetMins() { return CVector3D(min_x, min_y, min_z); }
	CVector3D GetMaxs() { return CVector3D(max_x, max_y, max_z); }


	double min_x, max_x;
	double min_y, max_y;
	double min_z, max_z;
};

class CMatrix
{
public:
	CMatrix();
	CMatrix& operator=(const SMatrix2& R);
	~CMatrix() {}

	CVector3D Transform(CVector3D& p);
	CVector3D TransformDir(CVector3D& p);
	CBoundingBox Transform(CBoundingBox& R);

	CVector3D GetAxis(int axis);
	bool TestMirror();

	double scale;
	bool is_identity;
	bool is_orthogonal;
	double m[4][3];
};

#endif