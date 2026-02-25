/**
 * MACRO API ROUTES — B1
 * 
 * API endpoints for macro data platform.
 * 
 * ISOLATION: No imports from DXY/BTC/SPX modules
 */

import { FastifyInstance, FastifyRequest, FastifyReply } from 'fastify';
import {
  ingestAllMacroSeries,
  ingestMacroSeries,
  getAllSeriesMeta,
  getMacroSeriesPoints,
} from '../ingest/macro.ingest.service.js';
import { buildMacroContext, buildAllMacroContexts } from '../services/macro_context.service.js';
import { computeMacroScore, computeMacroScoreAsOf } from '../services/macro_score.service.js';
import { buildHousingContext } from '../services/housing_context.service.js';
import { buildActivityContext } from '../services/activity_context.service.js';
import { buildCreditContext } from '../services/credit_context.service.js';
import { validateStability, validateEpisodes } from '../services/macro_stability_validation.service.js';
import { getDefaultMacroSeries, MACRO_SERIES_REGISTRY } from '../data/macro_sources.registry.js';
import { checkFredHealth, hasFredApiKey } from '../ingest/fred.client.js';

// P3: Import lag profiles
import { getAllLagProfiles } from '../../macro-asof/asof.service.js';

// ═══════════════════════════════════════════════════════════════
// REGISTER ROUTES
// ═══════════════════════════════════════════════════════════════

export async function registerMacroRoutes(fastify: FastifyInstance): Promise<void> {
  const prefix = '/api/dxy-macro-core';
  
  // ─────────────────────────────────────────────────────────────
  // Health check
  // ─────────────────────────────────────────────────────────────
  
  fastify.get(`${prefix}/health`, async (req, reply) => {
    const fredHealth = await checkFredHealth();
    const seriesMeta = await getAllSeriesMeta();
    
    return {
      ok: true,
      module: 'dxy-macro-core',
      version: 'B4.3',  // Updated for credit
      fred: {
        ...fredHealth,
        hasApiKey: hasFredApiKey(),
        keyHelp: 'Get free key at https://fred.stlouisfed.org/docs/api/api_key.html',
      },
      seriesLoaded: seriesMeta.length,
      defaultSeries: getDefaultMacroSeries().length,
    };
  });
  
  // ─────────────────────────────────────────────────────────────
  // GET /series — List all available series
  // ─────────────────────────────────────────────────────────────
  
  fastify.get(`${prefix}/series`, async (req, reply) => {
    const metas = await getAllSeriesMeta();
    const registry = MACRO_SERIES_REGISTRY;
    
    // Combine registry info with loaded data info
    const series = registry.map(spec => {
      const meta = metas.find(m => m.seriesId === spec.seriesId);
      return {
        seriesId: spec.seriesId,
        displayName: spec.displayName,
        frequency: spec.frequency,
        role: spec.role,
        units: spec.units,
        enabledByDefault: spec.enabledByDefault,
        loaded: !!meta,
        pointCount: meta?.pointCount ?? 0,
        firstDate: meta?.firstDate ?? null,
        lastDate: meta?.lastDate ?? null,
        coverageYears: meta?.coverageYears ?? 0,
      };
    });
    
    return {
      ok: true,
      total: registry.length,
      enabled: registry.filter(s => s.enabledByDefault).length,
      loaded: metas.length,
      series,
    };
  });
  
  // ─────────────────────────────────────────────────────────────
  // GET /context — Get context for a single series
  // ─────────────────────────────────────────────────────────────
  
  fastify.get(`${prefix}/context`, async (req: FastifyRequest, reply: FastifyReply) => {
    const query = req.query as { seriesId?: string };
    const seriesId = query.seriesId;
    
    if (!seriesId) {
      // Return all contexts
      const contexts = await buildAllMacroContexts();
      return {
        ok: true,
        count: contexts.length,
        contexts,
      };
    }
    
    // Single series context
    const context = await buildMacroContext(seriesId);
    
    if (!context) {
      return reply.code(404).send({
        ok: false,
        error: 'NOT_FOUND',
        message: `Series ${seriesId} not found or insufficient data`,
      });
    }
    
    return {
      ok: true,
      context,
    };
  });
  
  // ─────────────────────────────────────────────────────────────
  // GET /score — Get composite macro score
  // ─────────────────────────────────────────────────────────────
  
  fastify.get(`${prefix}/score`, async (
    req: FastifyRequest<{ Querystring: { asOf?: string } }>,
    reply: FastifyReply
  ) => {
    const { asOf } = req.query;
    
    if (asOf) {
      // P3: As-of mode
      const score = await computeMacroScoreAsOf(asOf);
      return { ok: true, score, mode: 'as-of' };
    }
    
    const score = await computeMacroScore();
    return { ok: true, score, mode: 'current' };
  });
  
  // ─────────────────────────────────────────────────────────────
  // P3: GET /lag-profiles — List publication lag profiles
  // ─────────────────────────────────────────────────────────────
  
  fastify.get(`${prefix}/lag-profiles`, async (req, reply) => {
    const profiles = getAllLagProfiles();
    return {
      ok: true,
      count: profiles.length,
      profiles,
      note: 'Publication lag in days for each series. Used for honest backtesting.',
    };
  });
  
  // ─────────────────────────────────────────────────────────────
  // GET /housing — Get housing context (B4.1)
  // ─────────────────────────────────────────────────────────────
  
  fastify.get(`${prefix}/housing`, async (req, reply) => {
    const housing = await buildHousingContext();
    
    return {
      ok: true,
      housing,
    };
  });
  
  // ─────────────────────────────────────────────────────────────
  // GET /activity — Get economic activity context (B4.2)
  // ─────────────────────────────────────────────────────────────
  
  fastify.get(`${prefix}/activity`, async (req, reply) => {
    const activity = await buildActivityContext();
    
    return {
      ok: true,
      activity,
    };
  });
  
  // ─────────────────────────────────────────────────────────────
  // GET /credit — Get credit & financial stress context (B4.3)
  // ─────────────────────────────────────────────────────────────
  
  fastify.get(`${prefix}/credit`, async (req, reply) => {
    const credit = await buildCreditContext();
    
    return {
      ok: true,
      credit,
    };
  });
  
  // ─────────────────────────────────────────────────────────────
  // GET /history — Get historical data for a series
  // ─────────────────────────────────────────────────────────────
  
  fastify.get(`${prefix}/history`, async (req: FastifyRequest, reply: FastifyReply) => {
    const query = req.query as { seriesId?: string; from?: string; to?: string };
    const { seriesId, from, to } = query;
    
    if (!seriesId) {
      return reply.code(400).send({
        ok: false,
        error: 'MISSING_PARAM',
        message: 'seriesId is required',
      });
    }
    
    const points = await getMacroSeriesPoints(seriesId, from, to);
    
    return {
      ok: true,
      seriesId,
      count: points.length,
      from: points[0]?.date ?? null,
      to: points[points.length - 1]?.date ?? null,
      points,
    };
  });
  
  // ─────────────────────────────────────────────────────────────
  // POST /admin/ingest — Ingest macro data from FRED
  // ─────────────────────────────────────────────────────────────
  
  fastify.post(`${prefix}/admin/ingest`, async (req: FastifyRequest, reply: FastifyReply) => {
    const body = req.body as { series?: string[] } | undefined;
    const seriesIds = body?.series;
    
    console.log(`[Macro API] Ingest request: ${seriesIds?.length ? seriesIds.join(', ') : 'all default'}`);
    
    const result = await ingestAllMacroSeries(seriesIds);
    
    return result;
  });
  
  // ─────────────────────────────────────────────────────────────
  // POST /admin/ingest/:seriesId — Ingest single series
  // ─────────────────────────────────────────────────────────────
  
  fastify.post(`${prefix}/admin/ingest/:seriesId`, async (req: FastifyRequest, reply: FastifyReply) => {
    const params = req.params as { seriesId: string };
    const { seriesId } = params;
    
    console.log(`[Macro API] Single ingest: ${seriesId}`);
    
    const result = await ingestMacroSeries(seriesId);
    
    return result;
  });
  
  // ─────────────────────────────────────────────────────────────
  // B5.1: GET /validate/stability — Stability validation
  // ─────────────────────────────────────────────────────────────
  
  fastify.get(`${prefix}/validate/stability`, async (req: FastifyRequest, reply: FastifyReply) => {
    const query = req.query as {
      from?: string;
      to?: string;
      step?: string;
      smooth?: string;
      span?: string;
    };
    
    const params = {
      from: query.from || '2000-01-01',
      to: query.to || '2025-12-31',
      stepDays: query.step ? parseInt(query.step) : 7,
      smooth: (query.smooth === 'ema' ? 'ema' : 'none') as 'ema' | 'none',
      span: query.span ? parseInt(query.span) : 14,
    };
    
    console.log(`[Macro B5.1] Stability validation: ${params.from} to ${params.to}, step=${params.stepDays}`);
    
    const report = await validateStability(params);
    
    return report;
  });
  
  // ─────────────────────────────────────────────────────────────
  // B5.2: GET /validate/episodes — Episode validation
  // ─────────────────────────────────────────────────────────────
  
  fastify.get(`${prefix}/validate/episodes`, async (req: FastifyRequest, reply: FastifyReply) => {
    const query = req.query as {
      smooth?: string;
      span?: string;
    };
    
    const smooth = query.smooth === 'ema' ? 'ema' : 'none';
    const span = query.span ? parseInt(query.span) : 14;
    
    console.log(`[Macro B5.2] Episode validation: smooth=${smooth}, span=${span}`);
    
    const report = await validateEpisodes(smooth as 'ema' | 'none', span);
    
    return report;
  });
  
  console.log(`[Macro] Routes registered at ${prefix}/* (B5 Validation)`);
}
