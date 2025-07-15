import gatewayClient from '@/lib/gateway-client';
import { NextRequest } from 'next/server';

export async function GET(req: NextRequest) {
    const url = new URL(req.url);
    const typeParams = url.searchParams.getAll('draft_type');
    const statusParams = url.searchParams.getAll('status');
    const search = url.searchParams.get('search') || undefined;
    // Use array if multiple, string if one, undefined if none
    const type = typeParams.length > 1 ? typeParams : typeParams.length === 1 ? typeParams[0] : undefined;
    const status = statusParams.length > 1 ? statusParams : statusParams.length === 1 ? statusParams[0] : undefined;
    try {
        const data = await gatewayClient.listDrafts({ type, status, search });
        return new Response(JSON.stringify(data), { status: 200, headers: { 'Content-Type': 'application/json' } });
    } catch (err: unknown) {
        return new Response(JSON.stringify({ error: (err as Error).message || 'Failed to fetch drafts' }), { status: 500 });
    }
}

export async function POST(req: NextRequest) {
    try {
        const body = await req.json();
        const data = await gatewayClient.createDraft(body);
        return new Response(JSON.stringify(data), { status: 200, headers: { 'Content-Type': 'application/json' } });
    } catch (err: unknown) {
        return new Response(JSON.stringify({ error: (err as Error).message || 'Failed to create draft' }), { status: 500 });
    }
}

export async function PUT(req: NextRequest) {
    try {
        const url = new URL(req.url);
        const id = url.searchParams.get('id');
        if (!id) return new Response(JSON.stringify({ error: 'Missing draft id' }), { status: 400 });
        const body = await req.json();
        const data = await gatewayClient.updateDraft(id, body);
        return new Response(JSON.stringify(data), { status: 200, headers: { 'Content-Type': 'application/json' } });
    } catch (err: unknown) {
        return new Response(JSON.stringify({ error: (err as Error).message || 'Failed to update draft' }), { status: 500 });
    }
}

export async function DELETE(req: NextRequest) {
    try {
        const url = new URL(req.url);
        const id = url.searchParams.get('id');
        if (!id) return new Response(JSON.stringify({ error: 'Missing draft id' }), { status: 400 });
        await gatewayClient.deleteDraft(id);
        return new Response(JSON.stringify({ success: true }), { status: 200, headers: { 'Content-Type': 'application/json' } });
    } catch (err: unknown) {
        return new Response(JSON.stringify({ error: (err as Error).message || 'Failed to delete draft' }), { status: 500 });
    }
} 