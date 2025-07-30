'use client';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import EmailView from '@/components/views/email-view';

export default function EmailDemoPage() {
    return (
        <div className="container mx-auto p-6 space-y-6">
            <div className="text-center space-y-2">
                <h1 className="text-3xl font-bold">Email Interface Demo</h1>
                <p className="text-muted-foreground">
                    A modern email interface including tight/expanded modes,
                    reading pane options, email threading, and hover actions.
                </p>
            </div>

            <Tabs defaultValue="features" className="w-full">
                <TabsList className="grid w-full grid-cols-3">
                    <TabsTrigger value="features">Features</TabsTrigger>
                    <TabsTrigger value="demo">Live Demo</TabsTrigger>
                    <TabsTrigger value="implementation">Implementation</TabsTrigger>
                </TabsList>

                <TabsContent value="features" className="space-y-4">
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        <Card>
                            <CardHeader>
                                <CardTitle className="flex items-center gap-2">
                                    <span className="text-blue-600">📧</span>
                                    Two View Modes
                                </CardTitle>
                            </CardHeader>
                            <CardContent>
                                <CardDescription>
                                    <strong>Tight Mode:</strong> One-line email cards with sender, subject, and snippet
                                    <br />
                                    <strong>Expanded Mode:</strong> Multi-line cards with full email details and actions
                                </CardDescription>
                            </CardContent>
                        </Card>

                        <Card>
                            <CardHeader>
                                <CardTitle className="flex items-center gap-2">
                                    <span className="text-green-600">👁️</span>
                                    Reading Pane Options
                                </CardTitle>
                            </CardHeader>
                            <CardContent>
                                <CardDescription>
                                    <strong>No Reading Pane:</strong> Full-width email list
                                    <br />
                                    <strong>Right Reading Pane:</strong> Split view with email preview
                                </CardDescription>
                            </CardContent>
                        </Card>

                        <Card>
                            <CardHeader>
                                <CardTitle className="flex items-center gap-2">
                                    <span className="text-purple-600">🧵</span>
                                    Email Threading
                                </CardTitle>
                            </CardHeader>
                            <CardContent>
                                <CardDescription>
                                    Emails are automatically grouped by thread with expandable conversation views
                                </CardDescription>
                            </CardContent>
                        </Card>

                        <Card>
                            <CardHeader>
                                <CardTitle className="flex items-center gap-2">
                                    <span className="text-orange-600">✨</span>
                                    Hover Actions
                                </CardTitle>
                            </CardHeader>
                            <CardContent>
                                <CardDescription>
                                    Action buttons appear on hover including archive, snooze, delete, and our magic wand tool
                                </CardDescription>
                            </CardContent>
                        </Card>

                        <Card>
                            <CardHeader>
                                <CardTitle className="flex items-center gap-2">
                                    <span className="text-red-600">📅</span>
                                    Smart Date Formatting
                                </CardTitle>
                            </CardHeader>
                            <CardContent>
                                <CardDescription>
                                    <strong>Today:</strong> Shows time (e.g., "2:30 PM")
                                    <br />
                                    <strong>Earlier:</strong> Shows date (e.g., "Jan 15")
                                </CardDescription>
                            </CardContent>
                        </Card>

                        <Card>
                            <CardHeader>
                                <CardTitle className="flex items-center gap-2">
                                    <span className="text-indigo-600">🎨</span>
                                    Modern UI
                                </CardTitle>
                            </CardHeader>
                            <CardContent>
                                <CardDescription>
                                    Clean, responsive design with proper spacing, typography, and visual hierarchy
                                </CardDescription>
                            </CardContent>
                        </Card>
                    </div>
                </TabsContent>

                <TabsContent value="demo" className="space-y-4">
                    <Card>
                        <CardHeader>
                            <CardTitle>Live Email Interface</CardTitle>
                            <CardDescription>
                                This demo shows the email interface in action.
                                Connect your email account to see real emails, or explore the interface features.
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            <div className="h-[600px] border rounded-lg overflow-hidden">
                                <EmailView
                                    toolDataLoading={false}
                                    activeTool="email"
                                />
                            </div>
                        </CardContent>
                    </Card>
                </TabsContent>

                <TabsContent value="implementation" className="space-y-4">
                    <Card>
                        <CardHeader>
                            <CardTitle>Implementation Details</CardTitle>
                            <CardDescription>
                                Technical details about how the email interface is implemented
                            </CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <div>
                                <h3 className="font-semibold mb-2">Components Created:</h3>
                                <ul className="list-disc list-inside space-y-1 text-sm">
                                    <li><code>EmailCard</code> - Individual email card with tight/expanded modes</li>
                                    <li><code>EmailThread</code> - Email threading with conversation grouping</li>
                                    <li><code>EmailView</code> - Main email interface with view controls</li>
                                </ul>
                            </div>

                            <div>
                                <h3 className="font-semibold mb-2">Key Features:</h3>
                                <ul className="list-disc list-inside space-y-1 text-sm">
                                    <li>Responsive design with Tailwind CSS</li>
                                    <li>State management for view modes and reading pane</li>
                                    <li>Email threading with automatic grouping</li>
                                    <li>Hover actions with smooth transitions</li>
                                    <li>Smart date formatting based on email age</li>
                                    <li>Integration with existing email services</li>
                                </ul>
                            </div>

                            <div>
                                <h3 className="font-semibold mb-2">Technical Stack:</h3>
                                <ul className="list-disc list-inside space-y-1 text-sm">
                                    <li>React with TypeScript</li>
                                    <li>Tailwind CSS for styling</li>
                                    <li>Lucide React for icons</li>
                                    <li>Existing email service integration</li>
                                    <li>Next.js for routing and SSR</li>
                                </ul>
                            </div>
                        </CardContent>
                    </Card>
                </TabsContent>
            </Tabs>
        </div>
    );
} 