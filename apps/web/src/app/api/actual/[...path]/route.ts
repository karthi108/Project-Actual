import { bridge } from "@/lib/bridge";
export const dynamic = "force-dynamic";
type Context = { params: Promise<{ path: string[] }> };
async function handle(request: Request, context: Context) {
  return bridge(request, (await context.params).path);
}
export { handle as GET, handle as POST };
