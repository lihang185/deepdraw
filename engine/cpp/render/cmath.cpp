#include <tchar.h>
#include <assert.h>
#include <vector>
#include <set>
#include <string>
#include <stdio.h>
#include <stdarg.h>
#include <map>
#include <windows.h>
#include <GL/GL.h>
#include "cmath.h"
#include "DeepDrawAPI.h"


//=====================
//  CVector3D
//
//=====================
CVector3D& CVector3D::operator=(const SVector3D& R) {
	x = R.x; y = R.y; z = R.z;
	return *this;
}

CVector3D CVector3D::operator*(double scale)
{
	CVector3D out;
	out.x = x * scale;
	out.y = y * scale;
	out.z = z * scale;
	return out;
}

double& CVector3D::operator[](int i) {
	if (i == 0) {
		return x;
	}
	else if (i == 1) {
		return y;
	}
	else {
		return z;
	}
}

bool CVector3D::Normalize()
{
	double length = sqrt(x * x + y * y + z * z);
	if (length < EPS2) {
		x = 0.0;
		y = 0.0;
		z = 0.0;
		return false;
	}
	else if (fabs(1.0 - length) < EPS2) {
		return true;
	}
	else {
		double s = 1.0 / length;
		x *= s;
		y *= s;
		z *= s;
		return true;
	}
}

CVector3D CVector3D::Cross(CVector3D& R)
{
	CVector3D out;
	out.x = y * R.z - z * R.y;
	out.y = z * R.x - x * R.z;
	out.z = x * R.y - y * R.x;
	return out;
}

double CVector3D::Dot(CVector3D& R)
{
	return x * R.x + y * R.y + z * R.z;
}

//=====================
//  CBoundingBox
//
//=====================
CBoundingBox::CBoundingBox()
{
	Reset();
}

CBoundingBox& CBoundingBox::operator=(const SBoundingBox& R)
{
	memcpy(this, &R, sizeof(R));
	return *this;
}

void CBoundingBox::Reset()
{
	min_x = INF_MAX;
	max_x = -INF_MAX;
	min_y = INF_MAX;
	max_y = -INF_MAX;
	min_z = INF_MAX;
	max_z = -INF_MAX;
}

SBoundingBox CBoundingBox::ToSBoundingBox()
{
	SBoundingBox sbox;
	memcpy(&sbox, this, sizeof(sbox));
	return sbox;
}

void CBoundingBox::Extend(CVector3D& p)
{
	// part x
	if (p.x < min_x)
		min_x = p.x;
	if (p.x > max_x)
		max_x = p.x;
	// part y
	if (p.y < min_y)
		min_y = p.y;
	if (p.y > max_y)
		max_y = p.y;
	// part z
	if (p.z < min_z)
		min_z = p.z;
	if (p.z > max_z)
		max_z = p.z;
}

//=====================
//  CMatrix
//
//=====================
CMatrix::CMatrix()
{
	m[0][0] = 1.0;
	m[0][1] = 0.0;
	m[0][2] = 0.0;

	m[1][0] = 0.0;
	m[1][1] = 1.0;
	m[1][2] = 0.0;

	m[2][0] = 0.0;
	m[2][1] = 0.0;
	m[2][2] = 1.0;

	m[3][0] = 0.0;
	m[3][1] = 0.0;
	m[3][2] = 0.0;

	scale = 1.0;
	is_identity = true;
	is_orthogonal = true;
}

CMatrix& CMatrix::operator=(const SMatrix2& R)
{
	scale = R.scale;
	is_identity = R.is_identity;
	is_orthogonal = R.is_orthogonal;
	memcpy(&m, &R.m, sizeof(R.m));
	return *this;
}


CVector3D CMatrix::Transform(CVector3D& v)
{
	CVector3D out;
	out.x = (v.x * m[0][0] + v.y * m[0][1] + v.z * m[0][2] + m[3][0]) * scale;
	out.y = (v.x * m[1][0] + v.y * m[1][1] + v.z * m[1][2] + m[3][1]) * scale;
	out.z = (v.x * m[2][0] + v.y * m[2][1] + v.z * m[2][2] + m[3][2]) * scale;
	return out;
}

CVector3D CMatrix::TransformDir(CVector3D& dir)
{
	CVector3D out;
	out.x = (dir.x * m[0][0] + dir.y * m[0][1] + dir.z * m[0][2]) * scale;
	out.y = (dir.x * m[1][0] + dir.y * m[1][1] + dir.z * m[1][2]) * scale;
	out.z = (dir.x * m[2][0] + dir.y * m[2][1] + dir.z * m[2][2]) * scale;
	return out;
}


CBoundingBox CMatrix::Transform(CBoundingBox& R)
{
	CVector3D mins;
	CVector3D maxs;
	CVector3D p1;
	CVector3D p2;
	CVector3D scaled_p1;
	CVector3D scaled_p2;
	CBoundingBox new_bbox;

	double xa, xb, ya, yb, za, zb;

	if (R.min_x <= R.max_x) {
		//if (!is_identity && R.min_x <= R.max_x) {
		mins = R.GetMins();
		maxs = R.GetMaxs();

		p1.x = p2.x = m[3][0];
		p1.y = p2.y = m[3][1];
		p1.z = p2.z = m[3][2];

		for (int i = 0; i < 3; i++) {
			xa = m[i][0] * mins.x;
			xb = m[i][0] * maxs.x;
			if (xb <= xa) {
				p1[i] += xb;
				p2[i] += xa;
			}
			else {
				p1[i] += xa;
				p2[i] += xb;
			}
			//save result

			ya = m[i][1] * mins.y;
			yb = m[i][1] * maxs.y;
			if (yb <= ya) {
				p1[i] += yb;
				p2[i] += ya;
			}
			else {
				p1[i] += ya;
				p2[i] += yb;
			}
			//save result

			za = m[i][2] * mins.z;
			zb = m[i][2] * maxs.z;
			if (zb <= za) {
				p1[i] += zb;
				p2[i] += za;
			}
			else {
				p1[i] += za;
				p2[i] += zb;
			}
			//save result
		}
		scaled_p1 = p1 * scale;
		scaled_p2 = p2 * scale;

		new_bbox.Extend(scaled_p1);
		new_bbox.Extend(scaled_p2);
	}
	return new_bbox;
}

CVector3D CMatrix::GetAxis(int axis)
{
	CVector3D out;
	out.x = m[0][axis];
	out.y = m[1][axis];
	out.z = m[2][axis];
	return out;
}

bool CMatrix::TestMirror()
{
	CVector3D xaxis = GetAxis(0);
	CVector3D yaxis = GetAxis(1);
	CVector3D zaxis = GetAxis(2);
	CVector3D dir = xaxis.Cross(yaxis);
	if (dir.Dot(zaxis) < 0.0)
		return true;
	return false;
}