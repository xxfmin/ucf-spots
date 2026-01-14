import { NextResponse } from "next/server";
import { createClient } from "@supabase/supabase-js";

// Force dynamic rendering (no caching)
export const dynamic = "force-dynamic";

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { feedback } = body;

    // Validate input
    if (!feedback || typeof feedback !== "string") {
      return NextResponse.json(
        { error: "Feedback text is required" },
        { status: 400 }
      );
    }

    if (feedback.length < 10 || feedback.length > 1000) {
      return NextResponse.json(
        { error: "Feedback must be between 10 and 1000 characters" },
        { status: 400 }
      );
    }

    // Get Supabase client
    // Support both naming conventions
    const supabaseUrl =
      process.env.SUPABASE_URL || process.env.NEXT_PUBLIC_SUPABASE_URL;
    const supabaseKey =
      process.env.SUPABASE_KEY || process.env.SUPABASE_SERVICE_ROLE_KEY;

    if (!supabaseUrl || !supabaseKey) {
      console.error("Missing Supabase environment variables");
      return NextResponse.json(
        { error: "Server configuration error" },
        { status: 500 }
      );
    }

    const supabase = createClient(supabaseUrl, supabaseKey);

    // Get client info (optional)
    const userAgent = request.headers.get("user-agent") || null;
    const forwarded = request.headers.get("x-forwarded-for");
    const ipAddress = forwarded ? forwarded.split(",")[0] : null;

    // Insert feedback into database
    const { data, error } = await supabase
      .from("feedback")
      .insert({
        feedback_text: feedback,
        user_agent: userAgent,
        ip_address: ipAddress,
      })
      .select()
      .single();

    if (error) {
      console.error("Error inserting feedback:", error);
      return NextResponse.json(
        { error: "Failed to save feedback" },
        { status: 500 }
      );
    }

    return NextResponse.json(
      { success: true, id: data.id },
      { status: 200 }
    );
  } catch (error: unknown) {
    console.error("Error in /api/feedback:", error);
    const errorMessage =
      error instanceof Error ? error.message : "Failed to submit feedback";
    return NextResponse.json({ error: errorMessage }, { status: 500 });
  }
}
