
import { useState } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Search, Filter, X, SlidersHorizontal } from "lucide-react";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";

interface SearchFilters {
  search: string;
  category: string;
  model: string;
  modalities: string[];
  capabilities: string[];
  status: string;
  sortBy: string;
  sortOrder: 'asc' | 'desc';
}

interface SearchAndFiltersProps {
  filters: SearchFilters;
  onFiltersChange: (filters: SearchFilters) => void;
  isLoading?: boolean;
  resultCount?: number;
}

const SearchAndFilters = ({ filters, onFiltersChange, isLoading, resultCount }: SearchAndFiltersProps) => {
  const [showAdvanced, setShowAdvanced] = useState(false);

  const categories = [
    "Code Generation", "Data Analysis", "Content Creation", 
    "Automation", "Research", "Customer Service", "Design", "Marketing"
  ];

  const models = ["GPT-4", "Claude 3.5", "LangChain", "Custom", "Gemini"];
  
  const modalities = ["Text", "Vision", "Audio", "Multimodal"];
  const capabilities = [
    "Code Generation", "Data Analysis", "Web Search", "File Processing",
    "API Integration", "Database Queries", "Image Generation", "Text Processing"
  ];

  const handleFilterChange = (key: keyof SearchFilters, value: any) => {
    // Convert "all" values back to empty strings for the filter logic
    const actualValue = value === "all" ? "" : value;
    onFiltersChange({ ...filters, [key]: actualValue });
  };

  const handleArrayFilterChange = (key: 'modalities' | 'capabilities', value: string, checked: boolean) => {
    const currentArray = filters[key];
    const newArray = checked 
      ? [...currentArray, value]
      : currentArray.filter(item => item !== value);
    
    onFiltersChange({ ...filters, [key]: newArray });
  };

  const clearFilters = () => {
    onFiltersChange({
      search: '',
      category: '',
      model: '',
      modalities: [],
      capabilities: [],
      status: '',
      sortBy: 'created_at',
      sortOrder: 'desc'
    });
  };

  const activeFilterCount = [
    filters.category,
    filters.model,
    filters.status,
    ...filters.modalities,
    ...filters.capabilities
  ].filter(Boolean).length;

  return (
    <Card className="card-elevated">
      <CardHeader className="pb-4">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg flex items-center">
            <Search className="w-5 h-5 mr-2" />
            Search & Filters
          </CardTitle>
          <div className="flex items-center space-x-2">
            {resultCount !== undefined && (
              <Badge variant="secondary">
                {resultCount.toLocaleString()} results
              </Badge>
            )}
            {activeFilterCount > 0 && (
              <Button 
                variant="outline" 
                size="sm" 
                onClick={clearFilters}
                className="text-xs"
              >
                <X className="w-3 h-3 mr-1" />
                Clear ({activeFilterCount})
              </Button>
            )}
          </div>
        </div>
      </CardHeader>
      
      <CardContent className="space-y-4">
        {/* Search Input */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground w-4 h-4" />
          <Input
            placeholder="Search agents by name, description, or tags..."
            value={filters.search}
            onChange={(e) => handleFilterChange('search', e.target.value)}
            className="pl-10"
            disabled={isLoading}
          />
        </div>

        {/* Quick Filters */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <Select value={filters.category || "all"} onValueChange={(value) => handleFilterChange('category', value)}>
            <SelectTrigger className="text-sm">
              <SelectValue placeholder="Category" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Categories</SelectItem>
              {categories.map((category) => (
                <SelectItem key={category} value={category}>
                  {category}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select value={filters.model || "all"} onValueChange={(value) => handleFilterChange('model', value)}>
            <SelectTrigger className="text-sm">
              <SelectValue placeholder="Model" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Models</SelectItem>
              {models.map((model) => (
                <SelectItem key={model} value={model}>
                  {model}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select value={filters.status || "all"} onValueChange={(value) => handleFilterChange('status', value)}>
            <SelectTrigger className="text-sm">
              <SelectValue placeholder="Status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Status</SelectItem>
              <SelectItem value="published">Published</SelectItem>
              <SelectItem value="draft">Draft</SelectItem>
              <SelectItem value="pending_review">Pending Review</SelectItem>
            </SelectContent>
          </Select>

          <Select 
            value={`${filters.sortBy}_${filters.sortOrder}`} 
            onValueChange={(value) => {
              const [sortBy, sortOrder] = value.split('_');
              handleFilterChange('sortBy', sortBy);
              handleFilterChange('sortOrder', sortOrder);
            }}
          >
            <SelectTrigger className="text-sm">
              <SelectValue placeholder="Sort By" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="created_at_desc">Newest First</SelectItem>
              <SelectItem value="created_at_asc">Oldest First</SelectItem>
              <SelectItem value="avg_rating_desc">Highest Rated</SelectItem>
              <SelectItem value="total_runs_desc">Most Popular</SelectItem>
              <SelectItem value="name_asc">Name A-Z</SelectItem>
              <SelectItem value="name_desc">Name Z-A</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Advanced Filters */}
        <Collapsible open={showAdvanced} onOpenChange={setShowAdvanced}>
          <CollapsibleTrigger asChild>
            <Button variant="outline" size="sm" className="w-full">
              <SlidersHorizontal className="w-4 h-4 mr-2" />
              Advanced Filters
              {activeFilterCount > 0 && (
                <Badge variant="secondary" className="ml-2 text-xs">
                  {activeFilterCount}
                </Badge>
              )}
            </Button>
          </CollapsibleTrigger>
          
          <CollapsibleContent className="pt-4 space-y-4">
            {/* Modalities */}
            <div>
              <Label className="text-sm font-medium mb-2 block">Modalities</Label>
              <div className="grid grid-cols-2 gap-2">
                {modalities.map((modality) => (
                  <div key={modality} className="flex items-center space-x-2">
                    <Checkbox 
                      id={`modality-${modality}`}
                      checked={filters.modalities.includes(modality)}
                      onCheckedChange={(checked) => handleArrayFilterChange('modalities', modality, !!checked)}
                    />
                    <Label htmlFor={`modality-${modality}`} className="text-sm">
                      {modality}
                    </Label>
                  </div>
                ))}
              </div>
            </div>

            {/* Capabilities */}
            <div>
              <Label className="text-sm font-medium mb-2 block">Capabilities</Label>
              <div className="grid grid-cols-2 gap-2">
                {capabilities.map((capability) => (
                  <div key={capability} className="flex items-center space-x-2">
                    <Checkbox 
                      id={`capability-${capability}`}
                      checked={filters.capabilities.includes(capability)}
                      onCheckedChange={(checked) => handleArrayFilterChange('capabilities', capability, !!checked)}
                    />
                    <Label htmlFor={`capability-${capability}`} className="text-sm">
                      {capability}
                    </Label>
                  </div>
                ))}
              </div>
            </div>
          </CollapsibleContent>
        </Collapsible>

        {/* Active Filters Display */}
        {activeFilterCount > 0 && (
          <div className="flex flex-wrap gap-2 pt-2 border-t">
            {filters.category && (
              <Badge variant="secondary" className="text-xs">
                Category: {filters.category}
                <Button 
                  variant="ghost" 
                  size="sm" 
                  className="h-auto p-0 ml-1 hover:bg-transparent"
                  onClick={() => handleFilterChange('category', 'all')}
                >
                  <X className="w-3 h-3" />
                </Button>
              </Badge>
            )}
            {filters.model && (
              <Badge variant="secondary" className="text-xs">
                Model: {filters.model}
                <Button 
                  variant="ghost" 
                  size="sm" 
                  className="h-auto p-0 ml-1 hover:bg-transparent"
                  onClick={() => handleFilterChange('model', 'all')}
                >
                  <X className="w-3 h-3" />
                </Button>
              </Badge>
            )}
            {filters.status && (
              <Badge variant="secondary" className="text-xs">
                Status: {filters.status}
                <Button 
                  variant="ghost" 
                  size="sm" 
                  className="h-auto p-0 ml-1 hover:bg-transparent"
                  onClick={() => handleFilterChange('status', 'all')}
                >
                  <X className="w-3 h-3" />
                </Button>
              </Badge>
            )}
            {filters.modalities.map((modality) => (
              <Badge key={modality} variant="secondary" className="text-xs">
                {modality}
                <Button 
                  variant="ghost" 
                  size="sm" 
                  className="h-auto p-0 ml-1 hover:bg-transparent"
                  onClick={() => handleArrayFilterChange('modalities', modality, false)}
                >
                  <X className="w-3 h-3" />
                </Button>
              </Badge>
            ))}
            {filters.capabilities.map((capability) => (
              <Badge key={capability} variant="secondary" className="text-xs">
                {capability}
                <Button 
                  variant="ghost" 
                  size="sm" 
                  className="h-auto p-0 ml-1 hover:bg-transparent"
                  onClick={() => handleArrayFilterChange('capabilities', capability, false)}
                >
                  <X className="w-3 h-3" />
                </Button>
              </Badge>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default SearchAndFilters;
