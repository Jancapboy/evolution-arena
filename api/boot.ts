import { Hono } from "hono";
import { bodyLimit } from "hono/body-limit";
import type { HttpBindings } from "@hono/node-server";
import { fetchRequestHandler } from "@trpc/server/adapters/fetch";
import { appRouter } from "./router";
import { createContext } from "./context";
import { env } from "./lib/env";

const app = new Hono<{ Bindings: HttpBindings }>();

app.use(bodyLimit({ maxSize: 50 * 1024 * 1024 }));
app.use("/api/trpc/*", async (c) => {
  return fetchRequestHandler({
    endpoint: "/api/trpc",
    req: c.req.raw,
    router: appRouter,
    createContext,
  });
});

// 反向代理到Python FastAPI后端（进化系统服务）
app.all("/api/*", async (c) => {
  const url = new URL(c.req.url);
  const target = `${env.pythonApiUrl}${url.pathname}${url.search}`;

  try {
    const body =
      c.req.method !== "GET" && c.req.method !== "HEAD"
        ? await c.req.arrayBuffer()
        : undefined;

    const res = await fetch(target, {
      method: c.req.method,
      headers: {
        "Content-Type": c.req.header("content-type") || "",
        Accept: c.req.header("accept") || "application/json",
      },
      body,
    });

    return new Response(res.body, {
      status: res.status,
      statusText: res.statusText,
      headers: {
        "Content-Type": res.headers.get("content-type") || "application/json",
      },
    });
  } catch (err: any) {
    return c.json(
      {
        error: "Python backend unreachable",
        detail: err.message,
        target,
      },
      502
    );
  }
});

export default app;

if (env.isProduction) {
  const { serve } = await import("@hono/node-server");
  const { serveStaticFiles } = await import("./lib/vite");
  serveStaticFiles(app);

  const port = parseInt(process.env.PORT || "3000");
  serve({ fetch: app.fetch, port }, () => {
    console.log(`Server running on http://localhost:${port}/`);
  });
}
