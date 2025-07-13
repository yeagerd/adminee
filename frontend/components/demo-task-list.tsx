"use client"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { ScrollArea } from "@/components/ui/scroll-area"
import { demoTasks } from "@/lib/demo-data"
import { CheckCircle, Circle, Clock, Plus } from "lucide-react"
import { useState } from "react"

export function DemoTaskList() {
    const [tasks, setTasks] = useState(demoTasks)

    const toggleTask = (taskId: string) => {
        setTasks(tasks.map(task =>
            task.id === taskId ? { ...task, completed: !task.completed } : task
        ))
    }

    const getPriorityColor = (priority: string) => {
        switch (priority) {
            case 'high':
                return 'bg-red-100 text-red-800'
            case 'medium':
                return 'bg-yellow-100 text-yellow-800'
            case 'low':
                return 'bg-green-100 text-green-800'
            default:
                return 'bg-gray-100 text-gray-800'
        }
    }

    const completedTasks = tasks.filter(task => task.completed)
    const pendingTasks = tasks.filter(task => !task.completed)

    return (
        <div className="space-y-4">
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <span className="text-sm text-muted-foreground">
                        {pendingTasks.length} pending, {completedTasks.length} completed
                    </span>
                </div>
                <Button variant="outline" size="sm">
                    <Plus className="h-4 w-4 mr-1" />
                    Add Task
                </Button>
            </div>

            <ScrollArea className="h-[300px] pr-4">
                <div className="space-y-3">
                    {/* Pending Tasks */}
                    {pendingTasks.map((task) => (
                        <div key={task.id} className="flex items-start gap-3 p-3 rounded-lg border bg-white">
                            <Checkbox
                                checked={task.completed}
                                onCheckedChange={() => toggleTask(task.id)}
                                className="mt-1"
                            />
                            <div className="flex-1 min-w-0">
                                <div className="flex items-start justify-between gap-2">
                                    <div className="flex-1 min-w-0">
                                        <h4 className="text-sm font-medium text-gray-900 truncate">
                                            {task.title}
                                        </h4>
                                        {task.description && (
                                            <p className="text-xs text-gray-600 mt-1 line-clamp-2">
                                                {task.description}
                                            </p>
                                        )}
                                    </div>
                                    <div className="flex items-center gap-2 flex-shrink-0">
                                        <Badge variant="outline" className={`text-xs ${getPriorityColor(task.priority)}`}>
                                            {task.priority}
                                        </Badge>
                                        {task.category && (
                                            <Badge variant="secondary" className="text-xs">
                                                {task.category}
                                            </Badge>
                                        )}
                                    </div>
                                </div>
                                {task.dueDate && (
                                    <div className="flex items-center gap-1 mt-2 text-xs text-gray-500">
                                        <Clock className="h-3 w-3" />
                                        <span>Due {task.dueDate.toLocaleDateString()}</span>
                                    </div>
                                )}
                            </div>
                        </div>
                    ))}

                    {/* Completed Tasks */}
                    {completedTasks.length > 0 && (
                        <div className="pt-4 border-t">
                            <h3 className="text-sm font-medium text-gray-700 mb-3">Completed</h3>
                            <div className="space-y-2">
                                {completedTasks.map((task) => (
                                    <div key={task.id} className="flex items-start gap-3 p-2 rounded-lg bg-gray-50">
                                        <CheckCircle className="h-4 w-4 text-green-500 mt-1 flex-shrink-0" />
                                        <div className="flex-1 min-w-0">
                                            <h4 className="text-sm font-medium text-gray-500 line-through truncate">
                                                {task.title}
                                            </h4>
                                            {task.description && (
                                                <p className="text-xs text-gray-400 mt-1 line-clamp-1">
                                                    {task.description}
                                                </p>
                                            )}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {tasks.length === 0 && (
                        <div className="text-center py-8">
                            <Circle className="h-12 w-12 mx-auto text-gray-400 mb-4" />
                            <h3 className="text-lg font-medium text-gray-900 mb-2">
                                No tasks yet
                            </h3>
                            <p className="text-gray-600 mb-4">
                                Create your first task to get started
                            </p>
                            <Button size="sm">
                                <Plus className="h-4 w-4 mr-2" />
                                Add Task
                            </Button>
                        </div>
                    )}
                </div>
            </ScrollArea>
        </div>
    )
} 