import { NextResponse } from 'next/server';
import clientPromise from '@/lib/mongodb';

/**
 * POST /api/auth
 * Body: { email: string }
 * Returns: { email, name, role, tenant_id, personal_email? }
 */
export async function POST(request) {
  try {
    const body = await request.json();
    const email = (body?.email || '').trim().toLowerCase();

    if (!email) {
      return NextResponse.json({ error: 'Email is required' }, { status: 400 });
    }

    const client = await clientPromise;
    const db = client.db('agentichr');

    const user = await db.collection('users').findOne(
      { email },
      { projection: { _id: 0, password: 0 } },
    );

    if (!user) {
      return NextResponse.json(
        { error: 'No account found for this email address.' },
        { status: 404 },
      );
    }

    // Map DB role → frontend role label
    // DB stores: "hr" | "employee"
    const roleMap = { hr: 'hr', employee: 'intern' };
    const role = roleMap[user.role] ?? 'intern';

    return NextResponse.json({
      email: user.email,
      name: user.full_name || user.name || email.split('@')[0],
      role,
      tenant_id: user.tenant_id || 'acme_corp',
      employee_id: user.employee_id || null,
      personal_email: user.personal_email || null,
    });
  } catch (err) {
    console.error('[auth] Error:', err);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}
