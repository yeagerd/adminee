"use client"

import type React from "react"

import { useState } from "react"
import { CheckCircle, Circle, Plus, Trash2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { ScrollArea } from "@/components/ui/scroll-area"

// Sample task data
const initialTasks = [
  { id: 1, text: "Prepare presentation for client meeting", completed: false },
  { id: 2, text: "Review project proposal", completed: true },
  { id: 3, text: "Send follow-up emails", completed: false },
  { id: 4, text: "Update weekly report", completed: false },
  { id: 5, text: "Schedule team building event", completed: false },
]

export default function TaskList() {
  const [tasks, setTasks] = useState(initialTasks)
  const [newTask, setNewTask] = useState("")

  const toggleTaskCompletion = (id: number) => {
    setTasks(tasks.map((task) => (task.id === id ? { ...task, completed: !task.completed } : task)))
  }

  const addTask = () => {
    if (newTask.trim()) {
      const newTaskObj = {
        id: Math.max(0, ...tasks.map((t) => t.id)) + 1,
        text: newTask.trim(),
        completed: false,
      }
      setTasks([...tasks, newTaskObj])
      setNewTask("")
    }
  }

  const deleteTask = (id: number) => {
    setTasks(tasks.filter((task) => task.id !== id))
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      addTask()
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex gap-2">
        <Input
          placeholder="Add a new task..."
          value={newTask}
          onChange={(e) => setNewTask(e.target.value)}
          onKeyDown={handleKeyDown}
          className="flex-1"
        />
        <Button onClick={addTask} size="sm">
          <Plus className="h-4 w-4 mr-1" />
          Add
        </Button>
      </div>

      <ScrollArea className="h-[300px] pr-4">
        <div className="space-y-2">
          {tasks.map((task) => (
            <div
              key={task.id}
              className={`flex items-center justify-between p-2 rounded-md ${
                task.completed ? "bg-gray-50" : "bg-white"
              } border`}
            >
              <div className="flex items-center gap-2 flex-1">
                <Button variant="ghost" size="icon" className="h-6 w-6" onClick={() => toggleTaskCompletion(task.id)}>
                  {task.completed ? (
                    <CheckCircle className="h-5 w-5 text-teal-600" />
                  ) : (
                    <Circle className="h-5 w-5 text-gray-400" />
                  )}
                </Button>
                <span className={task.completed ? "line-through text-gray-500" : ""}>{task.text}</span>
              </div>
              <Button
                variant="ghost"
                size="icon"
                className="h-6 w-6 opacity-50 hover:opacity-100"
                onClick={() => deleteTask(task.id)}
              >
                <Trash2 className="h-4 w-4 text-gray-500" />
              </Button>
            </div>
          ))}
        </div>
      </ScrollArea>
    </div>
  )
}
